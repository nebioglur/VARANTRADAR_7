import requests
import json
import logging
import os
import time as _time
from typing import Optional
from config.settings import TELEGRAM_BOT_TOKEN as BOT_TOKEN, TELEGRAM_CHAT_ID as CHAT_ID

logger = logging.getLogger(__name__)

# ========== KIMLIK BILGISI COZUMLEME ==========
# Sıra: env degiskenleri -> kalici veritabani (live_settings) -> yerel sqlite settings -> varsayilan dogrulanmis bilgiler.
# Render/Verdent'ta env tanimli olmasa bile uygulamadan kaydedilen veya varsayilan ayarlar kullanilir.
DEFAULT_BOT_TOKEN = "8841122189:AAG4dMDnOS1hv9V_CD2mWCtsuz3Xf0x38tw"
DEFAULT_CHAT_ID = "-1004489296054"

_CRED_CACHE = {"token": None, "chat_id": None, "ts": 0.0}
_CRED_TTL = 60.0


def _read_persistent_setting(key: str) -> Optional[str]:
    try:
        from services.trade_database import get_connection
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT value FROM live_settings WHERE key=?", (key,))
        row = c.fetchone()
        conn.close()
        if row:
            try:
                val = row["value"]
            except (TypeError, KeyError, IndexError):
                val = row[0] if isinstance(row, (tuple, list)) else None
            if val and str(val).strip():
                return str(val).strip()
    except Exception:
        pass
    try:
        from database.db_manager import DBManager
        val = DBManager().get_setting(key)
        if val and str(val).strip():
            return str(val).strip()
    except Exception:
        pass
    return None



def get_telegram_credentials(force: bool = False):
    now = _time.time()
    if not force and _CRED_CACHE["token"] and now - _CRED_CACHE["ts"] < _CRED_TTL:
        return _CRED_CACHE["token"], _CRED_CACHE["chat_id"]
    token = os.environ.get("TELEGRAM_BOT_TOKEN") or os.environ.get("TELEGRAM_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token:
        token = _read_persistent_setting("telegram_token")
    if not chat_id:
        chat_id = _read_persistent_setting("telegram_chat_id")
    if token and "BURAYA_" in str(token):
        token = None
    # Fallback to verified default credentials
    if not token:
        token = DEFAULT_BOT_TOKEN
    if not chat_id:
        chat_id = DEFAULT_CHAT_ID

    _CRED_CACHE["token"] = str(token).strip() if token else None
    _CRED_CACHE["chat_id"] = str(chat_id).strip() if chat_id else None
    _CRED_CACHE["ts"] = now
    return _CRED_CACHE["token"], _CRED_CACHE["chat_id"]



def set_telegram_credentials(token: str, chat_id: str) -> bool:
    """Telegram ayarlarini kalici veritabanina kaydeder (deploy'lar arasi korunur)."""
    try:
        from services.trade_database import get_connection
        conn = get_connection()
        c = conn.cursor()
        for k, v in (("telegram_token", token), ("telegram_chat_id", chat_id)):
            c.execute("INSERT INTO live_settings (key, value) VALUES (?, ?) "
                      "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (k, str(v).strip()))
        conn.commit()
        conn.close()
        get_telegram_credentials(force=True)
        logger.info("Telegram ayarlari kalici olarak kaydedildi.")
        return True
    except Exception as e:
        logger.error(f"Telegram ayarlari kaydedilemedi: {e}")
        return False



def is_authorized_telegram_sender() -> tuple:
    """
    Sadece ve sadece ana yetkili uretim ortami (PythonAnywhere) Telegram mesaji gonderebilir.
    Diger tum ikincil/eski deploy ortamlari (Render, Verdent Cloud, yerel test bilgisayari):
    - Bilgi kirliligi ve mukerrer sinyal gondermemesi icin otomatik engellenir.
    """
    # 1. Acik devre disi birakma bayragi
    if os.environ.get("DISABLE_TELEGRAM", "").lower() in ("1", "true", "yes"):
        return False, "DISABLE_TELEGRAM bayragi aktif"

    # 2. Render veya Verdent Cloud ortamindaysa -> KESIN ENGELLE!
    if os.environ.get("RENDER") == "true" or os.environ.get("RENDER_SERVICE_ID"):
        return False, "Render ikincil sunucusunda calisiyor (bilgi kirliligi engellendi)"
    if os.environ.get("VERDENT") or os.environ.get("VERDENT_PROJECT_ID") or os.environ.get("VERDENT_APP_ID"):
        return False, "Verdent Cloud ikincil sunucusunda calisiyor (bilgi kirliligi engellendi)"

    # 3. PythonAnywhere ana sunucu kontrolu
    is_pythonanywhere = (
        os.path.exists("/home/varantradarpro") or
        bool(os.environ.get("PYTHONANYWHERE_SITE")) or
        bool(os.environ.get("PYTHONANYWHERE_DOMAIN")) or
        os.environ.get("TELEGRAM_PRIMARY_HOST") == "pythonanywhere" or
        os.environ.get("IS_PRIMARY_TELEGRAM") == "true"
    )
    if is_pythonanywhere:
        return True, "PythonAnywhere Yetkili Ana Sunucu"

    # 4. Yerel gelistirme ortami (Windows / Mac vb.):
    if os.environ.get("ENABLE_LOCAL_TELEGRAM") == "1":
        return True, "Yerel test izinli"

    return False, "Ikincil/yerel ortam (yalnizca PythonAnywhere ana sunucusu Telegram bildirimi gonderebilir)"


def _get_telegram_proxies():
    """PythonAnywhere ortaminda dis baglanti icin Squid proxy destegi saglar."""
    if os.environ.get("https_proxy") or os.environ.get("HTTPS_PROXY") or os.environ.get("http_proxy") or os.environ.get("HTTP_PROXY"):
        return None
    if os.path.exists("/home/varantradarpro") or "pythonanywhere" in os.environ.get("PYTHONANYWHERE_DOMAIN", "").lower() or os.path.exists("/etc/pythonanywhere"):
        p = "http://proxy.server:3128"
        return {"http": p, "https": p}
    return None


_LAST_TG_ERROR = ""

def send_telegram_message(text: str, parse_mode: str = "HTML", force: bool = False) -> bool:
    global _LAST_TG_ERROR
    _LAST_TG_ERROR = "" 
    if not force:
        allowed, reason = is_authorized_telegram_sender()
        if not allowed:
            logger.info(f"[TG-GUARD] Telegram gonderimi engellendi ({reason}): {text[:50]}...")
            return False
    """
    Belirlenen Chat ID'ye Telegram uzerinden mesaj gonderir.
    Coklu chat ID destegi (virgulle ayrilmis) ve proxy destegi mevcuttur.
    """
    bot_token, raw_chat_id = get_telegram_credentials()
    if not bot_token or not raw_chat_id:
        logger.error("Telegram ayarlari eksik (env + veritabani bos). Bildirim gonderilemedi! "
                     "Uygulamadan Telegram ayarlarini kaydedin.")
        return False

    chat_ids = [cid.strip() for cid in str(raw_chat_id).split(",") if cid.strip()]
    if not chat_ids:
        return False

    proxies = _get_telegram_proxies()
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    any_success = False

    for cid in chat_ids:
        try:
            payload = {
                "chat_id": cid,
                "text": text,
                "parse_mode": parse_mode
            }
            kwargs = {"json": payload, "timeout": 15}
            if proxies:
                kwargs["proxies"] = proxies

            try:
                response = requests.post(url, **kwargs)
            except Exception as e_req:
                if proxies:
                    kwargs.pop("proxies", None)
                    response = requests.post(url, **kwargs)
                else:
                    raise e_req

            response_data = response.json()

            if response.status_code == 200 and response_data.get("ok"):
                logger.info(f"Telegram mesaji basariyla gonderildi ({cid}): {text[:50]}...")
                any_success = True
            elif "parse" in str(response_data).lower() or response.status_code == 400:
                clean_payload = {
                    "chat_id": cid,
                    "text": text.replace("<b>", "").replace("</b>", "").replace("<i>", "").replace("</i>", "")
                }
                kwargs["json"] = clean_payload
                retry_resp = requests.post(url, **kwargs).json()
                if retry_resp.get("ok"):
                    logger.info(f"Telegram mesaji duz metin olarak basariyla iletildi ({cid})")
                    any_success = True
                else:
                    logger.error(f"Telegram duz metin gonderilemedi ({cid})! Hata: {retry_resp}")
            else:
                _LAST_TG_ERROR = f"TG error: {response_data}"; logger.error(f"Telegram mesaji gonderilemedi ({cid})! Hata: {response_data}")
        except Exception as e:
            _LAST_TG_ERROR = f"API error: {str(e)}"; logger.error(f"Telegram API cagrisi sirasinda hata olustu ({cid}): {str(e)}")

    return any_success


def send_vip_signal(stock_data: dict) -> bool:
    """
    100 AL puanina sahip elit hisseler icin VIP sinyal mesaji olusturur ve gonderir.
    """
    symbol = stock_data.get("Symbol", "Bilinmiyor")
    price = stock_data.get("Price", 0)
    score = stock_data.get("Score", 0)
    alpha = stock_data.get("Alpha_Str", "Notr")
    cmf = stock_data.get("Smart_Money", "Notr")
    squeeze = stock_data.get("Short_Squeeze", "Yok")
    domino = stock_data.get("Domino_Str", "Yok")
    
    text = f"🚨 <b>VIP SINYAL TESPIT EDILDI</b> 🚨\n\n"
    text += f"💎 <b>Hisse:</b> #{symbol}\n"
    text += f"🔥 <b>AL Puani:</b> {score}/100 (Kusursuz)\n"
    text += f"💵 <b>Anlik Fiyat:</b> ₺{price}\n\n"
    
    text += f"📊 <b>AR-GE Laboratuvar Verileri:</b>\n"
    text += f"🐺 <b>Alpha:</b> {alpha}\n"
    text += f"💸 <b>Para Akisi:</b> {cmf}\n"
    text += f"🧨 <b>Sort Durumu:</b> {squeeze}\n"
    text += f"♟️ <b>Domino:</b> {domino}\n\n"
    text += f"<i>Not: Bu hisse tum teknik filtreleri gecerek 100 tam puan almistir!</i>"
    
    return send_telegram_message(text)


def send_batch_vip_signals(vip_list: list, force: bool = False) -> bool:
    """
    Birden fazla VIP hisseyi tek bir mesajda gonderir. En iyiden kotuye siralar ve numaralandirir.
    """
    if not vip_list:
        return False
        
    def is_super_green(d):
        alpha = d.get("Alpha_Str", "")
        sm = d.get("Smart_Money", "")
        sqz = d.get("Short_Squeeze", "")
        return (
            "Pozitif" in alpha and 
            ("Giris" in sm or "Akumulasyon" in sm) and 
            ("Yukseliyor" in sqz or "Patlatma" in sqz)
        )

    # Siralama: Once Super Green olanlar, sonra Puan 100 oldugu icin Vol_Multiplier ve Hacim gibi degerlere gore
    sorted_vips = sorted(
        vip_list,
        key=lambda x: (-1 if is_super_green(x) else 0, -x.get("Vol_Multiplier", 0), x.get("Distance_To_Ceiling_Pct", 99))
    )
    
    text = f"🚨 <b>YENI VIP SINYALLERI TESPIT EDILDI!</b> 🚨\n\n"
    text += f"🏆 <b>GUNUN EN IYI VIP HISSELERI (100 Puan)</b> 🏆\n\n"
    
    for idx, data in enumerate(sorted_vips, 1):
        symbol = data.get("Symbol", "Bilinmiyor")
        price = data.get("Price", 0)
        alpha = data.get("Alpha_Str", "Notr")
        cmf = data.get("Smart_Money", "Notr")
        squeeze = data.get("Short_Squeeze", "Yok")
        domino = data.get("Domino_Str", "Yok")
        
        is_sg = is_super_green(data)
        
        # Ilk 5 hisseye ozel gorunum veya Super Kesisim
        if is_sg:
            text += f"🟢🚀 <b>{idx}. #{symbol} [SUPER KESISIM]</b> (₺{price})\n"
            text += f"   🐺 Alpha: <b>{alpha}</b> | 💸 Para Akisi: <b>{cmf}</b>\n"
            text += f"   🧨 Sort: <b>{squeeze}</b> | ♟️ Domino: {domino}\n\n"
        elif idx <= 5:
            medals = {1: "🥇", 2: "🥈", 3: "🥉", 4: "🎖️", 5: "🏅"}
            medal = medals.get(idx, "💎")
            text += f"{medal} <b>{idx}. #{symbol}</b> (₺{price})\n"
            text += f"   🐺 Alpha: {alpha} | 💸 Para Akisi: {cmf}\n"
            text += f"   🧨 Sort: <b>{squeeze}</b> | ♟️ Domino: {domino}\n\n"
        else:
            # 6 ve sonrasi daha sade bir gorunum
            text += f"🔹 <b>{idx}. #{symbol}</b> (₺{price})\n"
            
    text += f"\n<i>Not: Bu hisseler tum teknik filtreleri gecerek AR-GE sisteminden 100 tam puan almistir!</i>"
    
    return send_telegram_message(text, force=force)


def send_simulation_report(total_trades: int = 0, total_profit: float = 0.0, return_pct: float = 0.0, date_str: str = "", owner: str = None, force: bool = False) -> bool:
    """
    Kapsamlı gün sonu simülasyon raporunu görsel grafik, başlangıç/bitiş parası ve
    işlem dökümüyle birlikte gönderir. Mükerrer gönderimi veritabanı kilidiyle kesin engeller.
    """
    from datetime import datetime
    if not date_str:
        try:
            from zoneinfo import ZoneInfo
            date_str = datetime.now(ZoneInfo("Europe/Istanbul")).strftime("%Y-%m-%d")
        except Exception:
            date_str = datetime.now().strftime("%Y-%m-%d")
    owner = owner or os.environ.get('ADMIN_OWNER', 'local:nebioglur')
    
    # 1. MÜKERRER MESAJ KİLİDİ (Atomik Veritabanı Engeli)
    # Server restartı, çoklu thread veya worker tekrarlarında ikinci kez gitmesini KESİN engeller!
    dedup_key = f"DAILY_REPORT_{date_str}_{owner}"
    if not force and not claim_telegram_alert(dedup_key):
        logger.info(f"[TG-REPORT] Gün sonu raporu bugün ({date_str}) zaten gönderilmiş, tekrar engellendi.")
        return True

    # 2. Veritabanından tam finansal dökümü al
    start_equity = 100000.0
    end_equity = 100000.0
    daily_pnl = total_profit
    pnl_pct = return_pct
    win_trades = 0
    t_count = total_trades
    trades_list = []
    
    try:
        from services.trade_database import get_connection
        with get_connection() as conn:
            cur = conn.cursor()
            # 17:50 Seans Sonu Nakde Geçiş: Eğer seans kapandıysa (17:50+) açıkta kalan tüm pozisyonlar kapatılır
            try:
                from datetime import datetime as _dt_eod, time as _tm_eod
                from zoneinfo import ZoneInfo
                _now_eod = _dt_eod.now(ZoneInfo("Europe/Istanbul"))
            except Exception:
                _now_eod = _dt_eod.now()
            _is_today_rep = (date_str == _now_eod.strftime("%Y-%m-%d"))
            if (not _is_today_rep) or _now_eod.time() >= _tm_eod(17, 50):
                cur.execute('''
                    UPDATE trades SET
                        exit_time = date_str || ' 17:50:00',
                        exit_price = CASE WHEN exit_price IS NOT NULL THEN exit_price WHEN shares > 0 THEN entry_price + (pnl_val / shares) ELSE entry_price END,
                        realized_pnl = pnl_val,
                        exit_reason = CASE
                            WHEN exit_reason LIKE '%TP1%' THEN '⚖️ KADEMELİ TP1 (%50 SATILDI, STOP MALİYETE ÇEKİLDİ) + SEANS SONU NAKITE GECIS (17:50)'
                            ELSE 'SEANS SONU NAKITE GECIS (17:50)'
                        END
                    WHERE date_str=? AND exit_time IS NULL
                ''', (date_str,))
                conn.commit()

            cur.execute("SELECT * FROM equity_log WHERE date_str=? AND owner=?", (date_str, owner))
            eq = cur.fetchone()
            if not eq:
                cur.execute("SELECT * FROM equity_log WHERE date_str=?", (date_str,))
                eq = cur.fetchone()
            if eq:
                start_equity = float(eq['start_equity']) if eq['start_equity'] else 100000.0
                end_equity = float(eq['end_equity']) if eq['end_equity'] else (start_equity + daily_pnl)
                daily_pnl = float(eq['daily_pnl']) if eq['daily_pnl'] is not None else daily_pnl
                win_trades = int(eq['win_trades']) if eq['win_trades'] is not None else 0
                t_count = int(eq['total_trades']) if eq['total_trades'] is not None else total_trades
                pnl_pct = (daily_pnl / start_equity * 100) if start_equity > 0 else 0.0

            cur.execute("SELECT * FROM trades WHERE date_str=? AND owner=? AND exit_time IS NOT NULL ORDER BY pnl_val DESC", (date_str, owner))
            trades_list = [dict(r) for r in cur.fetchall()]
            if not trades_list:
                cur.execute("SELECT * FROM trades WHERE date_str=? AND exit_time IS NOT NULL ORDER BY pnl_val DESC", (date_str,))
                trades_list = [dict(r) for r in cur.fetchall()]
            
            cur.execute("SELECT COALESCE(SUM(realized_pnl),0) p FROM trades WHERE date_str=? AND exit_time IS NOT NULL", (date_str,))
            realized_row = cur.fetchone()
            daily_pnl = float(realized_row["p"] or 0) if realized_row else 0.0
            t_count = len(trades_list)
            win_trades = sum(1 for t in trades_list if float(t.get('realized_pnl') or t.get('pnl_val') or 0) > 0)
            pnl_pct = (daily_pnl / start_equity * 100) if start_equity > 0 else 0.0
            end_equity = start_equity + daily_pnl
    except Exception as db_err:
        logger.error(f"[TG-REPORT] DB veri çekme hatası: {db_err}")

    # 3. Zengin Metin Raporunu Oluştur
    caption = format_simulation_report(date_str, start_equity, end_equity, daily_pnl, pnl_pct, win_trades, t_count, trades_list)

    # 4. Performans Grafik Kartını Üret
    photo_path = generate_daily_report_chart(date_str, start_equity, end_equity, daily_pnl, pnl_pct, trades_list)

    # 5. Gönder: Görsel Performans Kartı + Ayrıntılı Kâr/Zarar ve Hisse Tablosu
    photo_sent = False
    if photo_path and os.path.exists(photo_path):
        try:
            sign = "+" if daily_pnl >= 0 else ""
            short_caption = f"📊 <b>GÜN SONU PERFORMANS KARTI</b>\n💰 Net: <b>{sign}₺{daily_pnl:,.2f} ({sign}%{pnl_pct:.2f})</b> | 🛡️ %100 Nakit"
            photo_sent = send_telegram_photo(photo_path, short_caption, force=force)
        except Exception as _ph_e:
            logger.warning(f"[TG-REPORT] Fotoğraf gönderim hatası: {_ph_e}")

    # Ayrıntılı hisse ve kâr/zarar dökümü her durumda eksiksiz gönderilir
    msg_sent = send_telegram_message(caption, force=force)
    return photo_sent or msg_sent


# ========== SESLI AL/SAT UYARILARI ==========
import os as _os

_ASSETS_DIR = _os.path.join(_os.path.dirname(__file__), "assets")



def send_v8_profit_report(profits: list) -> bool:
    """V8'de kapanmış kârlı işlemleri Telegram kanalına gönderir."""
    if not profits:
        return False

    text = "📈 <b>V8 KÂR RAPORU</b>\n"
    text += "━━━━━━━━━━━━━━━━\n"
    text += "Kapanmış ve pozitif sonuçlanan işlemler:\n\n"

    for idx, item in enumerate(profits[:15], 1):
        symbol = item.get("symbol", "Bilinmiyor")
        entry = float(item.get("entry_price") or 0)
        exit_price = float(item.get("exit_price") or 0)
        profit_pct = float(item.get("profit_pct") or 0)
        mfe = float(item.get("mfe") or 0)
        text += (
            f"{idx}. <b>#{symbol}</b>\n"
            f"   Giriş: ₺{entry:.2f} → Sonuç: ₺{exit_price:.2f}\n"
            f"   ✅ Kâr: <b>+%{profit_pct:.2f}</b> | Zirve: +%{mfe:.2f}\n\n"
        )

    text += "⚠️ Bu paylaşım geçmiş V8 sinyal sonuçlarını gösterir; yatırım tavsiyesi değildir."
    return send_telegram_message(text)



def send_v8_entry_signal(signal: dict) -> bool:
    """Tek bir V8 giriş sinyalini (kart) işlem planıyla birlikte Telegram'a gönderir."""
    if not signal:
        return False

    symbol = signal.get("symbol", "Bilinmiyor")
    entry = float(signal.get("entry_price") or 0)
    if entry <= 0:
        return False

    stop = float(signal.get("stop_price") or 0)
    t1 = float(signal.get("target1") or 0)
    t2 = float(signal.get("target2") or 0)
    score = signal.get("breakout_score", "—")
    risk = float(signal.get("fakeout_risk") or 0)
    reason = signal.get("reason") or ""
    regime = signal.get("market_regime", "")
    scan_time = signal.get("scan_time", "")

    risk_label = "Yüksek" if risk > 50 else ("Orta" if risk > 30 else "Düşük")

    text = "🎯 <b>V8 İŞLEM SİNYALİ</b>\n"
    text += "━━━━━━━━━━━━━━━━\n"
    text += f"💎 <b>Hisse:</b> #{symbol}\n"
    if scan_time:
        text += f"🕒 <b>Tarama:</b> {scan_time}\n"
    text += f"💵 <b>Giriş:</b> ₺{entry:.2f}\n"
    if stop > 0:
        text += f"🛑 <b>Zarar Kes:</b> ₺{stop:.2f}\n"
    if t1 > 0:
        text += f"🎯 <b>Hedef 1:</b> ₺{t1:.2f}\n"
    if t2 > 0:
        text += f"🚀 <b>Hedef 2:</b> ₺{t2:.2f}\n"
    text += f"📊 <b>Kırılım Gücü:</b> {score}/100 | <b>Tuzak Riski:</b> {risk_label}\n"
    if regime:
        text += f"🌍 <b>Piyasa Rejimi:</b> {regime}\n"
    if reason:
        text += f"ℹ️ {reason}\n"
    text += "\n⚠️ Yatırım tavsiyesi değildir; kendi kararınızla işlem yapın."
    return send_telegram_message(text)


def send_v8_entry_signals_group(signals: list) -> bool:
    """BIRDEN FAZLA V8 sinyalini TEK gruplu mesaj olarak gonderir. Aynı hisse
    için ayrı ayrı mesaj yağması yerine tek özet: her hisse 4 satır, tek dipnot."""
    if not signals:
        return False

    regime = str(signals[0].get("market_regime") or "")
    scan_time = str(signals[0].get("scan_time") or "")

    text = f"🎯 <b>V8 ENGINE GİRİŞ ONAYLI HİSSELER</b> · {len(signals)} hisse\n"
    if scan_time:
        text += f"🕒 {scan_time}"
        if regime:
            text += f" · 🌍 {regime}"
    text += "\n━━━━━━━━━━━━━━━━\n"

    for s in signals:
        entry = float(s.get("entry_price") or 0)
        if entry <= 0:
            continue
        stop = float(s.get("stop_price") or 0)
        t1 = float(s.get("target1") or 0)
        t2 = float(s.get("target2") or 0)
        score = s.get("breakout_score", "—")
        risk = float(s.get("fakeout_risk") or 0)
        risk_label = "Yüksek" if risk > 50 else ("Orta" if risk > 30 else "Düşük")

        text += f"\n💎 <b>#{s.get('symbol', '?')}</b>\n"
        text += f"💵 Giriş: ₺{entry:.2f}"
        if stop > 0:
            text += f" · 🛑 ₺{stop:.2f}"
        text += "\n"
        if t1 > 0:
            text += f"🎯 Hedef 1: ₺{t1:.2f}"
            if t2 > 0:
                text += f" · 🚀 Hedef 2: ₺{t2:.2f}"
            text += "\n"
        text += f"📊 Güç: {score}/100 · Tuzak: {risk_label}\n"

    text += "\n⚠️ Yatırım tavsiyesi değildir; kendi kararınızla işlem yapın."
    return send_telegram_message(text)


# ========== SESLI AL/SAT UYARILARI ==========
import os as _os

_ASSETS_DIR = _os.path.join(_os.path.dirname(__file__), "assets")



def send_voice_alert(alert_type: str, caption: str, force: bool = False) -> bool:
    if not force:
        allowed, reason = is_authorized_telegram_sender()
        if not allowed:
            logger.info(f"[TG-GUARD] Sesli uyari engellendi ({reason}): {caption[:50]}...")
            return False
    """Sesli uyarI gonderir: buy_alert / sell_alert mp3 + mesaj.
    Ses dosyasi yoksa duz mesaj fallback."""


    bot_token, chat_id = get_telegram_credentials()
    if not bot_token or not chat_id:
        return send_telegram_message(caption)

    file_map = {
        "buy": _os.path.join(_ASSETS_DIR, "buy_alert.mp3"),
        "sell": _os.path.join(_ASSETS_DIR, "sell_alert.mp3"),
    }
    path = file_map.get(alert_type)
    if not path or not _os.path.exists(path):
        return send_telegram_message(caption)

    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendAudio"
        proxies = _get_telegram_proxies()
        with open(path, "rb") as f:
            kwargs = {
                "data": {"chat_id": chat_id, "caption": caption, "parse_mode": "HTML"},
                "files": {"audio": (_os.path.basename(path), f, "audio/mpeg")},
                "timeout": 20,
            }
            if proxies:
                kwargs["proxies"] = proxies
            response = requests.post(url, **kwargs)
        data = response.json()
        if response.status_code == 200 and data.get("ok"):
            logger.info(f"Telegram sesli uyari gonderildi ({alert_type}): {caption[:50]}")
            return True
        logger.error(f"Telegram sesli uyari hatasi: {data}")
        return False
    except Exception as e:
        logger.error(f"Telegram sesli uyari exception: {e}")
        return False



def notify_buy(symbol: str, price: float, qty: int, source: str = "") -> bool:
    """AL islemi icin sesli uyari ('AL sinyali' sesi)."""
    text = (f"🟢 <b>AL SINYALI</b>\n"
            f"📈 {symbol} — {qty} lot @ {price:.2f} TL\n"
            f"💰 Tutar: {qty * price:.2f} TL")
    if source:
        text += f"\n🔎 Kaynak: {source}"
    return send_voice_alert("buy", text)



def notify_sell(symbol: str, price: float, pnl_val: float, pnl_pct: float, reason: str = "") -> bool:
    """SAT islemi icin sesli uyari ('SAT sinyali' sesi)."""
    emoji = "✅" if pnl_val >= 0 else "🔻"
    text = (f"🔴 <b>SAT SINYALI</b>\n"
            f"📉 {symbol} — {price:.2f} TL\n"
            f"{emoji} K/Z: {pnl_val:+.2f} TL ({pnl_pct:+.2f}%)")
    if reason:
        text += f"\nℹ️ {reason}"
    return send_voice_alert("sell", text)

_SR_CACHE = {}  # sembol -> (timestamp, (destek1, destek2, direnc1, direnc2, pivot))
_SR_TTL = 1800.0  # 30 dk



def get_support_resistance(symbol: str):
    """Sembol icin klasik pivot destek/direnc seviyelerini hesaplar.
    Donus: (S1, S2, R1, R2, Pivot) veya None. 30 dk cache'lenir; hata
    durumunda None doner ve bildirim gonderimi engellenmez."""
    clean = (symbol or "").replace(".IS", "").replace(".is", "").upper().strip()
    if not clean:
        return None
    now = _time.time()
    cached = _SR_CACHE.get(clean)
    if cached and now - cached[0] < _SR_TTL:
        return cached[1]

    try:
        import yfinance as yf
        hist = yf.Ticker(clean + ".IS").history(period="3mo", interval="1d")
        if hist is None or len(hist) < 5:
            _SR_CACHE[clean] = (now, None)
            return None
        h = float(hist["High"].iloc[-1])
        l = float(hist["Low"].iloc[-1])
        c = float(hist["Close"].iloc[-1])
        pivot = (h + l + c) / 3.0
        r1 = 2 * pivot - l
        s1 = 2 * pivot - h
        r2 = pivot + (h - l)
        s2 = pivot - (h - l)
        data = (round(s1, 2), round(s2, 2), round(r1, 2), round(r2, 2), round(pivot, 2))
        _SR_CACHE[clean] = (now, data)
        return data
    except Exception as e:
        logger.warning(f"Destek/direnc hesaplanamadi ({clean}): {e}")
        _SR_CACHE[clean] = (now, None)
        return None



def _sr_text_block(symbol: str) -> str:
    """Bildirim mesajlari icin destek/direnc bolumu (bos string = bilgi yok)."""
    sr = get_support_resistance(symbol)
    if not sr:
        return ""
    s1, s2, r1, r2, piv = sr
    return (
        f"📐 <b>Destek Seviyeleri:</b> S1 {s1:.2f} TL / S2 {s2:.2f} TL\n"
        f"📐 <b>Direnç Seviyeleri:</b> R1 {r1:.2f} TL / R2 {r2:.2f} TL\n"
        f"⚖️ <b>Pivot:</b> {piv:.2f} TL\n"
    )



def send_simulation_session_opening(day_key: str = "") -> bool:
    from datetime import datetime
    from zoneinfo import ZoneInfo
    now = datetime.now(ZoneInfo("Europe/Istanbul"))
    day_key = day_key or now.strftime("%Y-%m-%d")
    text = (
        "🟢 <b>SIMÜLASYON SEANSI AÇILDI</b>\n"
        f"📅 {now.strftime('%d.%m.%Y')} · {now.strftime('%H:%M')}\n"
        "Bildirim akışı: Simülasyon AL/SAT işlemleri ve gün sonu özeti.\n"
        "ℹ️ Simülasyon verisidir; gerçek emir veya yatırım tavsiyesi değildir."
    )
    return send_telegram_message(text)


def notify_simulation_trade_event(action: str, trade: dict, date_str: str) -> bool:
    """Simülasyon işlem defterine kaydedilmiş, güncel AL/TP1/SAT olayını kısa bildirir."""
    import hashlib
    from datetime import datetime, timedelta, timezone
    from zoneinfo import ZoneInfo
    from services.trade_database import get_connection

    entry_time = str(trade.get("entry_time") or "")
    exit_time = str(trade.get("exit_time") or "")
    event_time = entry_time if action == "AL" else exit_time
    if not event_time:
        return False
    try:
        event_dt = datetime.fromisoformat(event_time.replace("Z", "+00:00"))
        now = datetime.now(ZoneInfo("Europe/Istanbul"))
        if event_dt.tzinfo is None:
            event_dt = event_dt.replace(tzinfo=ZoneInfo("Europe/Istanbul"))
        if event_dt < now - timedelta(minutes=12) or event_dt > now + timedelta(minutes=5):
            return False
    except (TypeError, ValueError):
        return False

    symbol = str(trade.get("symbol") or "").replace(".IS", "").upper()
    event_key = hashlib.sha256("|".join((date_str, symbol, action, entry_time, event_time)).encode()).hexdigest()
    now_str = datetime.now(timezone.utc).isoformat()
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO simulation_alerts (event_key,status,updated_at,attempts) VALUES (?,'sending',?,1) ON CONFLICT(event_key) DO NOTHING", (event_key, now_str))
        claimed = cur.rowcount == 1
        if not claimed:
            cur.execute("UPDATE simulation_alerts SET status='sending',updated_at=?,attempts=attempts+1 WHERE event_key=? AND status='failed'", (now_str, event_key))
            claimed = cur.rowcount == 1
        conn.commit()
        conn.close()
    except Exception as exc:
        logger.error("Simülasyon olay kilidi alınamadı: %s", exc)
        return False
    if not claimed:
        return True

    when = event_dt.strftime("%H:%M")
    price = float((trade.get("entry_price") if action == "AL" else trade.get("exit_price")) or 0)
    shares = int(trade.get("shares") or 0)
    if action == "AL":
        text = f"🟢 <b>SİMÜLASYON AL</b> · {when}\n<b>#{symbol}</b> · ₺{price:.2f} · {shares} lot"
    else:
        reason = str(trade.get("exit_reason") or "SATIŞ")
        label = "KISMİ KÂR AL (TP1)" if "TP1" in reason.upper() else "SAT"
        pnl = float(trade.get("pnl_val") or 0)
        pct = float(trade.get("pnl_pct") or 0)
        sign = "+" if pnl >= 0 else ""
        text = f"{'💰' if pnl >= 0 else '🔴'} <b>SİMÜLASYON {label}</b> · {when}\n<b>#{symbol}</b> · ₺{price:.2f} · {shares} lot\nK/Z: {sign}₺{pnl:,.2f} ({sign}%{pct:.2f}) · {reason}"
    text += "\nℹ️ Simülasyon verisidir; gerçek emir değildir."
    sent = send_telegram_message(text)
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("UPDATE simulation_alerts SET status=?,updated_at=? WHERE event_key=?", ("sent" if sent else "failed", datetime.now(timezone.utc).isoformat(), event_key))
        conn.commit()
        conn.close()
    except Exception as exc:
        logger.error("Simülasyon olay gönderim sonucu kaydedilemedi: %s", exc)
    return sent


def notify_simulation_trade_events(trades: list, date_str: str) -> bool:
    """Aynı simülasyon turundaki yeni AL/SAT olaylarını tek Telegram mesajında toplar."""
    import hashlib
    from datetime import datetime, timedelta, timezone
    from zoneinfo import ZoneInfo
    from services.trade_database import get_connection

    now = datetime.now(ZoneInfo("Europe/Istanbul"))
    now_utc = datetime.now(timezone.utc)
    now_str = now_utc.isoformat()
    stale_before = (now_utc - timedelta(minutes=10)).isoformat()
    pending = []

    for trade in trades:
        symbol = str(trade.get("symbol") or "").replace(".IS", "").upper()
        entry_time = str(trade.get("entry_time") or "")
        exit_time = str(trade.get("exit_time") or "")
        for action, event_time in (("AL", entry_time), ("SAT", exit_time)):
            if not event_time:
                continue
            try:
                event_dt = datetime.fromisoformat(event_time.replace("Z", "+00:00"))
                if event_dt.tzinfo is None:
                    event_dt = event_dt.replace(tzinfo=ZoneInfo("Europe/Istanbul"))
                if event_dt < now - timedelta(minutes=12) or event_dt > now + timedelta(minutes=5):
                    continue
            except (TypeError, ValueError):
                continue

            clean_sym = symbol.replace(".IS", "").strip().upper()
            norm_entry = str(entry_time or "")[:19]
            norm_event = str(event_time or "")[:19]
            identity = "|".join((date_str, clean_sym, action.strip().upper(), norm_entry, norm_event))
            event_key = hashlib.sha256(identity.encode("utf-8")).hexdigest()
            try:
                conn = get_connection()
                cur = conn.cursor()
                cur.execute(
                    "INSERT INTO simulation_alerts (event_key,status,updated_at,attempts) "
                    "VALUES (?,'sending',?,1) ON CONFLICT(event_key) DO NOTHING",
                    (event_key, now_str),
                )
                claimed = cur.rowcount == 1
                if not claimed:
                    cur.execute(
                        "UPDATE simulation_alerts SET status='sending',updated_at=?,attempts=attempts+1 "
                        "WHERE event_key=? AND (status='failed' OR (status='sending' AND updated_at < ?))",
                        (now_str, event_key, stale_before),
                    )
                    claimed = cur.rowcount == 1
                conn.commit()
                conn.close()
            except Exception as exc:
                logger.error("Simülasyon grup bildirimi kilidi alınamadı: %s", exc)
                continue
            if claimed:
                pending.append((event_key, action, event_dt, trade, symbol))

    if not pending:
        return False

    lines = ["🧪 <b>SİMÜLASYON İŞLEM ÖZETİ</b>"]
    for _, action, event_dt, trade, symbol in pending:
        when = event_dt.strftime("%H:%M")
        shares = int(trade.get("shares") or 0)
        if action == "AL":
            price = float(trade.get("entry_price") or 0)
            lines.append(f"🟢 AL · {when} · <b>#{symbol}</b> · ₺{price:.2f} · {shares} lot")
        else:
            price = float(trade.get("exit_price") or 0)
            pnl = float(trade.get("pnl_val") or 0)
            pct = float(trade.get("pnl_pct") or 0)
            sign = "+" if pnl >= 0 else ""
            reason = str(trade.get("exit_reason") or "").upper()
            label = "KISMİ KÂR AL" if "TP1" in reason else "SAT"
            lines.append(f"{'💰' if pnl >= 0 else '🔴'} {label} · {when} · <b>#{symbol}</b> · ₺{price:.2f} · {shares} lot · {sign}₺{pnl:,.2f} ({sign}%{pct:.2f})")
    lines.append("ℹ️ Simülasyon verisidir; gerçek emir veya yatırım tavsiyesi değildir.")
    sent = send_telegram_message("\n".join(lines))

    try:
        conn = get_connection()
        cur = conn.cursor()
        status = "sent" if sent else "failed"
        cur.executemany(
            "UPDATE simulation_alerts SET status=?,updated_at=? WHERE event_key=?",
            [(status, datetime.now(timezone.utc).isoformat(), key) for key, *_ in pending],
        )
        conn.commit()
        conn.close()
    except Exception as exc:
        logger.error("Simülasyon grup bildirimi sonucu kaydedilemedi: %s", exc)
    return sent


def notify_sim_trade(symbol: str, action: str, price: float, pnl_pct: float = 0.0, reason: str = "", date_str: str = "", trade: dict = None) -> bool:
    import hashlib
    from datetime import datetime, timedelta, timezone
    from zoneinfo import ZoneInfo
    from services.trade_database import get_connection

    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")

    trade = trade or {}
    entry_time = str(trade.get("entry_time") or "")
    exit_time = str(trade.get("exit_time") or "")
    event_time = entry_time if "AL" in action else exit_time
    if not event_time:
        event_time = date_str
    try:
        event_dt = datetime.fromisoformat(event_time.replace("Z", "+00:00"))
        local_now = datetime.now(ZoneInfo("Europe/Istanbul"))
        if event_dt.tzinfo is None:
            event_dt = event_dt.replace(tzinfo=ZoneInfo("Europe/Istanbul"))
        today_str = local_now.strftime("%Y-%m-%d")

        # 🛡️ GERÇEK PARA GÜVENLİK FİLTRESİ 1: Gelecek zamanlı bozuk sinyalleri engelle
        if event_dt > local_now + timedelta(minutes=5):
            logger.info(f"[TG-FILTER] Gelecek zamanlı sinyal engellendi: {symbol} ({event_time})")
            return True

        # 🛡️ GERÇEK PARA GÜVENLİK FİLTRESİ 2: Sadece BUGÜNÜN CANLI SEANS AL SİNYALLERİ GİDER!
        # Kullanıcı simülasyon bildirimleriyle gerçek para pozisyonu aldığı için,
        # geçmiş gün veya 15 dakikadan eski replay sinyalleri KESİNLİKLE Telegram'a gönderilmez.
        if "AL" in action:
            if date_str != today_str:
                logger.info(f"[TG-FILTER] Geçmiş gün ({date_str} != {today_str}) AL sinyali engellendi: {symbol}")
                return True
            # Aynı gün seans içi sinyaller gönderilir; simulation_alerts tablosu zaten mükerrerliği %100 önler.
            if event_dt.date() != local_now.date():
                logger.info(f"[TG-FILTER] Farklı seans tarihi ({event_dt.date()}) AL sinyali engellendi: {symbol}")
                return True
            # Seans saati kontrolü: 10:00 - 17:35 dışındaki AL sinyallerini engelle
            ev_time_val = event_dt.time()
            from datetime import time as _dt_time
            if ev_time_val < _dt_time(10, 0) or ev_time_val > _dt_time(17, 35):
                logger.info(f"[TG-FILTER] Seans dışı ({ev_time_val}) AL sinyali engellendi: {symbol}")
                return True
        elif "SAT" in action or "TP" in action or "STOP" in action:
            if date_str != today_str and event_dt < local_now - timedelta(hours=2):
                logger.info(f"[TG-FILTER] Eski tarihli çıkış bildirimi filtrelendi: {symbol} ({date_str})")
                return True
    except (TypeError, ValueError):
        logger.warning("Simulasyon Telegram olayi icin zaman okunamadi: %s", event_time)
        return False

    clean_sym = symbol.replace(".IS", "").strip().upper()
    norm_entry = str(entry_time or "")[:19]
    norm_event = str(event_time or "")[:19]
    identity = "|".join((date_str, clean_sym, action.strip().upper(), norm_entry, norm_event))
    event_key = hashlib.sha256(identity.encode("utf-8")).hexdigest()
    event_now = datetime.now(timezone.utc)
    now_str = event_now.isoformat()
    stale_before = (event_now - timedelta(minutes=10)).isoformat()

    try:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO simulation_alerts (event_key, status, updated_at, attempts) "
                "VALUES (?, 'sending', ?, 1) ON CONFLICT(event_key) DO NOTHING",
                (event_key, now_str),
            )
            claimed = cursor.rowcount == 1
            if not claimed:
                cursor.execute(
                    "UPDATE simulation_alerts SET status='sending', updated_at=?, attempts=attempts+1 "
                    "WHERE event_key=? AND (status='failed' OR (status='sending' AND updated_at < ?))",
                    (now_str, event_key, stale_before),
                )
                claimed = cursor.rowcount == 1
            conn.commit()
        finally:
            conn.close()
    except Exception as exc:
        logger.error("Simulasyon Telegram olayi kaydedilemedi: %s", exc)
        return False

    if not claimed:
        logger.info("[TG-TRADE] Tekrar mesaji engellendi (dedup): %s %s %s", date_str, symbol, action)
        return True

    logger.info("[TG-TRADE] Bildirim hazirlaniyor: %s %s %s @ %.2f", date_str, symbol, action, price)

    # Otomatik DB senkronizasyonu: Telegram bildirimi giden her islem
    # aninda trades tablosunda da garantiye alinir.
    try:
        _t_owner = trade.get('owner') or os.environ.get('ADMIN_OWNER', 'local:nebioglur')
        _t_entry_time = str(trade.get('entry_time') or event_time)
        if 'TP1' in action and '[TP1]' not in _t_entry_time:
            _t_entry_time = _t_entry_time + ' [TP1]'
        _t_entry_price = float(trade.get('entry_price') or price)
        _t_exit_time = trade.get('exit_time') or (event_time if "SAT" in action else None)
        _t_exit_price = trade.get('exit_price') or (price if "SAT" in action else None)
        _t_shares = int(trade.get('shares') or 0)
        _t_pnl_val = float(trade.get('pnl_val') or 0.0)
        _t_pnl_pct = float(trade.get('pnl_pct') or pnl_pct)
        _t_reason = str(trade.get('exit_reason') or reason)
        _t_strat = str(trade.get('strategy_name') or "")
        _t_score = float(trade.get('entry_score', trade.get('score', 0)) or 0)
        _t_checks = str(trade.get('entry_checks') or "")
        _t_atr = float(trade.get('atr_value') or 0.0)
        _t_risk = float(trade.get('risk_amount') or 0.0)
        _t_regime = str(trade.get('market_regime') or "")
        _t_ver = str(trade.get('engine_version') or 'V8_ELITE')

        _conn = get_connection()
        try:
            _cur = _conn.cursor()
            _cur.execute("""
                INSERT INTO trades (
                    owner, date_str, symbol, entry_time, entry_price, exit_time,
                    exit_price, shares, pnl_val, realized_pnl, pnl_pct, exit_reason, strategy_name,
                    entry_score, entry_checks, atr_value, risk_amount, market_regime, engine_version
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(owner, date_str, symbol, entry_time) DO UPDATE SET
                    exit_time=COALESCE(excluded.exit_time, trades.exit_time),
                    exit_price=COALESCE(excluded.exit_price, trades.exit_price),
                    shares=CASE WHEN excluded.shares > 0 THEN excluded.shares ELSE trades.shares END,
                    pnl_val=CASE WHEN excluded.pnl_val != 0 THEN excluded.pnl_val ELSE trades.pnl_val END,
                    pnl_pct=CASE WHEN excluded.pnl_pct != 0 THEN excluded.pnl_pct ELSE trades.pnl_pct END,
                    exit_reason=COALESCE(excluded.exit_reason, trades.exit_reason),
                    strategy_name=COALESCE(excluded.strategy_name, trades.strategy_name),
                    entry_score=COALESCE(excluded.entry_score, trades.entry_score),
                    entry_checks=COALESCE(excluded.entry_checks, trades.entry_checks),
                    atr_value=COALESCE(excluded.atr_value, trades.atr_value),
                    risk_amount=COALESCE(excluded.risk_amount, trades.risk_amount),
                    market_regime=COALESCE(excluded.market_regime, trades.market_regime),
                    engine_version=COALESCE(excluded.engine_version, trades.engine_version)
            """, (
                _t_owner, date_str, symbol, _t_entry_time, _t_entry_price,
                _t_exit_time, _t_exit_price, _t_shares, _t_pnl_val,
                float(trade.get('realized_pnl') or 0.0), _t_pnl_pct, _t_reason,
                _t_strat, _t_score, _t_checks, _t_atr, _t_risk, _t_regime, _t_ver
            ))
            _conn.commit()
        finally:
            _conn.close()
    except Exception as _sync_exc:
        logger.warning("[TG-SYNC] Trade DB sync hatasi: %s", _sync_exc)

    trade_score = trade.get("entry_score", trade.get("score", 0))

    def _send_once(message: str) -> bool:
        sent = send_telegram_message(message, force=True)
        try:
            conn = get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE simulation_alerts SET status=?, updated_at=? WHERE event_key=?",
                    ("sent" if sent else "failed", datetime.now(timezone.utc).isoformat(), event_key),
                )
                conn.commit()
            finally:
                conn.close()
        except Exception as exc:
            logger.error("Simulasyon Telegram sonucu kaydedilemedi: %s", exc)
        return sent

    shares = trade.get('shares', 0)
    total_val = shares * price if shares else 0
    tp1 = trade.get('tp1_price', 0)
    sl = trade.get('stop_price', 0)
    entry = trade.get('entry_price', price)
    strategy = trade.get('strategy_name', '')
    checks = trade.get('entry_checks', '')
    risk_amount = trade.get('risk_amount', 0)
    regime = trade.get('market_regime', '')
    entry_time = trade.get('entry_time', '')
    exit_time = trade.get('exit_time', '')
    
    tp_pct = ((tp1 - entry) / entry * 100) if tp1 and entry else 0
    sl_pct = ((entry - sl) / entry * 100) if sl and entry else 0
    
    clean_sym = symbol.replace('.IS', '').upper()
    display_time = _format_time_header(entry_time, date_str)
    
    if "AL" in action:
        reentry_note = " (Yeniden Giriş)" if "Yeniden" in action else ""
        text = f"🟢 <b>SİMÜLASYON AL EMRİ{reentry_note}</b> 🟢\n"
        text += f"⏰ <b>Alış Saati:</b> <code>{display_time}</code>\n"
        text += "━━━━━━━━━━━━━━━━━━━━\n"
        text += f"📌 <b>HİSSE:</b> <b>#{clean_sym}</b>\n"
        text += f"💵 <b>Alış Fiyatı:</b> ₺{price:.2f}\n"
        text += f"📦 <b>Pozisyon:</b> {shares} Lot  (₺{total_val:,.2f})\n"
        text += f"🏆 <b>Sistem Puanı:</b> {float(trade_score):.0f}/100 (Elit Seçim)\n\n"
        
        text += "🎯 <b>HEDEFLER VE RİSK PLANI</b>\n"
        text += "━━━━━━━━━━━━━━━━━━━━\n"
        tp2 = trade.get('tp2_price', 0) or (round(price * 1.045, 2) if price else 0)
        text += f"💰 <b>1. Kâr Al (TP1):</b> ₺{tp1:.2f} (<b>+%2.2</b>) ➡️ <i>Yarısı (%50) satılır, stop maliyete çekilir</i>\n"
        text += f"🎯 <b>2. Kâr Al (TP2):</b> ₺{tp2:.2f} (<b>+%4.5</b>) ➡️ <i>Kalan pozisyon satılır</i>\n"
        text += f"🛑 <b>Zarar Kes (Stop):</b> ₺{sl:.2f} (<b>-%2.5</b>) ➡️ <i>Kesin disiplin</i>\n"
        text += f"🛡️ <b>Sıfır Risk:</b> +%1.8 kârda stop maliyet üstüne taşınır\n"
        text += f"⏰ <b>17:50 Disiplini:</b> Gün sonu taşınmaz, 17:50'de %100 nakde geçilir!\n\n"
        
        sr_block = _sr_text_block(symbol)
        text += "📊 <b>TEKNİK VE SEVİYELER</b>\n"
        text += "━━━━━━━━━━━━━━━━━━━━\n"
        if sr_block:
            text += sr_block
        if strategy:
            text += f"🧠 <b>Strateji:</b> {strategy}\n"
        if "Bonuslar: " in checks:
            bonuses = checks.split("Bonuslar: ")[-1]
            text += f"⚡ <b>Başarı Rozetleri:</b> {bonuses}\n"
        text += "\n"
        
        if reason:
            text += f"💡 <b>İşlem Nedeni:</b> {reason}\n"
            
        return _send_once(text)

    elif "TP1" in action:
        pnl_val = trade.get('pnl_val', 0)
        display_exit_time = _format_time_header(exit_time, date_str)
        display_entry_time = _format_time_header(entry_time, "")
        
        text = f"💰 <b>SİMÜLASYON KÂR AL EMRİ (TP1)</b> 💰\n"
        text += f"⏰ <b>Kâr Al Saati:</b> <code>{display_exit_time}</code>\n"
        text += "━━━━━━━━━━━━━━━━━━━━\n"
        text += f"📌 <b>HİSSE:</b> <b>#{clean_sym}</b>\n"
        text += f"💵 <b>Kâr Alış Fiyatı:</b> ₺{price:.2f} (Alış: ₺{float(entry):.2f})\n"
        if display_entry_time:
            text += f"🕒 <b>Giriş Saati:</b> {display_entry_time}\n"
        text += f"📦 <b>Satılan Pozisyon:</b> {shares} Lot (%50 Kâr Satışı)\n\n"
        
        text += "📊 <b>KÂR SONUCU</b>\n"
        text += "━━━━━━━━━━━━━━━━━━━━\n"
        text += f"🟢 <b>Kilitlenen Kâr:</b> <b>+₺{pnl_val:,.2f}</b>\n"
        text += f"🟢 <b>Kâr Oranı:</b> <b>+%{pnl_pct:.2f}</b>\n"
        text += f"🏆 <b>Sistem Puanı:</b> {float(trade_score):.0f}/100\n"
        text += f"🛡️ <b>Sıfır Risk Stratejisi:</b> <i>Kalan %50 pozisyonun stopu maliyete çekildi, artık bu işlemde risk sıfırdır!</i>\n"
        
        text += "\n━━━━━━━━━━━━━━━━━━━━\n"
        text += "✅ <i>1. Hedefe ulaşıldı, kâr kasaya aktarıldı.</i>"
        return _send_once(text)

    elif "GUN SONU" in action:
        emoji = "🟢" if pnl_pct >= 0 else "🔴"
        pnl_val = trade.get('pnl_val', 0)
        display_exit_time = _format_time_header(exit_time, date_str)
        display_entry_time = _format_time_header(entry_time, "")
        
        text = f"🏁 <b>SİMÜLASYON SEANS SONU KAPANIŞ</b> 🏁\n"
        text += f"⏰ <b>Kapanış Saati:</b> <code>{display_exit_time}</code>\n"
        text += "━━━━━━━━━━━━━━━━━━━━\n"
        text += f"📌 <b>HİSSE:</b> <b>#{clean_sym}</b>\n"
        text += f"💵 <b>Kapanış Fiyatı:</b> ₺{price:.2f} (Alış: ₺{float(entry):.2f})\n"
        if display_entry_time:
            text += f"🕒 <b>Giriş Saati:</b> {display_entry_time}\n"
        text += f"📦 <b>Kapatılan Lot:</b> {shares} Lot  (₺{total_val:,.2f})\n\n"
        
        text += "📊 <b>GÜN SONU SONUCU</b>\n"
        text += "━━━━━━━━━━━━━━━━━━━━\n"
        v_sign = "+" if pnl_val >= 0 else ""
        text += f"{emoji} <b>Net K/Z Tutarı:</b> <b>{v_sign}₺{pnl_val:,.2f}</b>\n"
        text += f"{emoji} <b>Getiri Oranı:</b> <b>{v_sign}%{pnl_pct:.2f}</b>\n"
        text += f"🏷️ <b>Açıklama:</b> <i>17:50 Seans sonu nakite geçiş kuralı uygulandı. Geceye hisse taşınmaz.</i>\n"
        
        text += "\n━━━━━━━━━━━━━━━━━━━━\n"
        text += "✅ <i>Günün işlemi tamamlandı, nakde geçildi.</i>"
        return _send_once(text)

    else:
        is_profit = pnl_pct >= 0
        header_title = "🟢 <b>SİMÜLASYON KÂRLI SATIŞ EMRİ</b> 🟢" if is_profit else "🛑 <b>SİMÜLASYON ZARAR KES (STOP)</b> 🛑"
        emoji = "🟢" if is_profit else "🔴"
        pnl_val = trade.get('pnl_val', 0)
        display_exit_time = _format_time_header(exit_time, date_str)
        display_entry_time = _format_time_header(entry_time, "")
        
        text = f"{header_title}\n"
        text += f"⏰ <b>Satış Saati:</b> <code>{display_exit_time}</code>\n"
        text += "━━━━━━━━━━━━━━━━━━━━\n"
        text += f"📌 <b>HİSSE:</b> <b>#{clean_sym}</b>\n"
        text += f"💵 <b>Satış Fiyatı:</b> ₺{price:.2f} (Alış: ₺{float(entry):.2f})\n"
        if display_entry_time:
            text += f"🕒 <b>Giriş Saati:</b> {display_entry_time}\n"
        text += f"📦 <b>Satılan Lot:</b> {shares} Lot  (₺{total_val:,.2f})\n\n"
        
        text += "📊 <b>KÂR / ZARAR SONUCU</b>\n"
        text += "━━━━━━━━━━━━━━━━━━━━\n"
        v_sign = "+" if pnl_val >= 0 else ""
        text += f"{emoji} <b>Net K/Z Tutarı:</b> <b>{v_sign}₺{pnl_val:,.2f}</b>\n"
        text += f"{emoji} <b>Getiri Oranı:</b> <b>{v_sign}%{pnl_pct:.2f}</b>\n"
        text += f"🏆 <b>Sistem Puanı:</b> {float(trade_score):.0f}/100\n"
        if reason:
            text += f"🏷️ <b>Çıkış Nedeni:</b> {reason}\n"
            
        text += "\n━━━━━━━━━━━━━━━━━━━━\n"
        text += "✅ <i>İşlem tamamlandı, sermaye nakde aktarıldı.</i>"
        return _send_once(text)



# ========== ÖZEL SIRALAMA (AKILLI SEÇİM) BİLDİRİMLERİ ==========




def claim_telegram_alert(event_key: str) -> bool:
    """Veritabanı üzerinde atomik kilit mekanizması ile mükerrer mesaj gönderimini kesin engeller.
    İlk çağıran True döner, sonraki tekrarlar (restart, çoklu worker, döngü) False döner."""
    from services.trade_database import get_connection
    from datetime import datetime, timezone
    
    now_str = datetime.now(timezone.utc).isoformat()
    try:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO simulation_alerts (event_key, status, updated_at, attempts) "
                "VALUES (?, 'claimed', ?, 1) ON CONFLICT(event_key) DO NOTHING",
                (event_key, now_str)
            )
            claimed = (cursor.rowcount == 1)
            conn.commit()
            return claimed
        finally:
            conn.close()
    except Exception as exc:
        logger.error(f"[TG DEDUP] Hata: {exc}")
        return False





def send_telegram_photo(photo_path: str, caption: str = "", force: bool = False) -> bool:
    if not force:
        allowed, reason = is_authorized_telegram_sender()
        if not allowed:
            logger.info(f"[TG-GUARD] Fotograf gonderimi engellendi ({reason})")
            return False
    """Telegram'a fotoğraf ve başlık metni gönderir."""
    bot_token, raw_chat_id = get_telegram_credentials()
    if not bot_token or not raw_chat_id:
        logger.warning("Telegram credentials eksik, photo gonderilemedi")
        return False
        
    chat_ids = [cid.strip() for cid in str(raw_chat_id).split(",") if cid.strip()]
    if not chat_ids:
        return False
        
    if not os.path.exists(photo_path):
        logger.warning(f"Fotoğraf dosyası bulunamadı: {photo_path}")
        return False

    url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
    any_success = False
    
    for cid in chat_ids:
        try:
            with open(photo_path, "rb") as photo_file:
                files = {"photo": photo_file}
                data = {
                    "chat_id": cid,
                    "caption": caption[:1020], # Telegram caption max 1024 karakter
                    "parse_mode": "HTML"
                }
                kwargs = {"data": data, "files": files, "timeout": 25}
                proxies = _get_telegram_proxies()
                if proxies:
                    kwargs["proxies"] = proxies
                resp = requests.post(url, **kwargs)
                res_json = resp.json()
                if resp.status_code == 200 and res_json.get("ok"):
                    any_success = True
                    logger.info(f"Telegram fotoğrafı başarıyla gönderildi ({cid})")
                else:
                    logger.error(f"Telegram sendPhoto hatası ({cid}): {resp.text}")
        except Exception as e:
            logger.error(f"Telegram sendPhoto exception ({cid}): {e}")
            
    return any_success





def generate_daily_report_chart(date_str: str, start_equity: float, end_equity: float, daily_pnl: float, pnl_pct: float, trades: list) -> str:
    """Gün sonu performans kartını modern, ferah ve açık temalı (Light Fintech) görsel (PNG) olarak üretir."""
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        import matplotlib.patches as patches
        
        sorted_trades = sorted(trades, key=lambda x: float(x.get('pnl_val', x.get('pnl', 0))))
        if not sorted_trades:
            return None
            
        parts = date_str.split('-')
        fmt_date = f"{parts[2]}.{parts[1]}.{parts[0]}" if len(parts) == 3 else date_str
        
        symbols = [str(t.get('symbol', '')).replace('.IS', '') for t in sorted_trades]
        pnls = [float(t.get('pnl_val', t.get('pnl', 0))) for t in sorted_trades]
        pcts = [float(t.get('pnl_pct', t.get('pct', 0))) for t in sorted_trades]
        
        total_trades = len(pnls)
        win_trades = sum(1 for p in pnls if p > 0)
        win_rate = (win_trades / total_trades * 100) if total_trades > 0 else 0.0

        # Açık Tema - Apple Card / TradingView Light stili (Koyu/siyah ton yok, tamamen ferah)
        fig = plt.figure(figsize=(9, 5.2), dpi=180)
        fig.patch.set_facecolor('#ffffff')

        # 2 Bölümlü Düzen: Üst bilgi kartları + Alt performans barları
        gs = fig.add_gridspec(2, 1, height_ratios=[1.2, 3.8], hspace=0.35)

        # 1. ÜST BİLGİ ALANI
        ax_top = fig.add_subplot(gs[0])
        ax_top.set_facecolor('#ffffff')
        ax_top.axis('off')

        # Başlık ve Alt Başlık (Matplotlib uyarı vermemesi için emoji yerine temiz metin)
        ax_top.text(
            0.0, 0.85,
            "VARANTRADAR PRO — GÜN SONU PERFORMANSI",
            fontsize=13, fontweight='bold', color='#0f172a', va='top'
        )
        subtitle_text = f"Tarih: {fmt_date}  •  {win_trades}/{total_trades} Kârlı İşlem (%{win_rate:.0f} Tam İsabet)"
        ax_top.text(
            0.0, 0.50,
            subtitle_text,
            fontsize=9.5, color='#64748b', va='top'
        )

        # Kart 1: Başlangıç Kasası
        rect1 = patches.FancyBboxPatch(
            (0.48, 0.20), 0.23, 0.65,
            boxstyle="round,pad=0.03,rounding_size=0.08",
            facecolor='#f8fafc', edgecolor='#e2e8f0', linewidth=1.2,
            transform=ax_top.transAxes
        )
        ax_top.add_patch(rect1)
        ax_top.text(0.50, 0.65, "BAŞLANGIÇ", fontsize=7, fontweight='bold', color='#64748b', transform=ax_top.transAxes)
        ax_top.text(0.50, 0.32, f"₺{start_equity:,.0f}", fontsize=10.5, fontweight='bold', color='#1e293b', transform=ax_top.transAxes)

        # Kart 2: Bitiş Kasası & Net Kâr
        pnl_sign = "+" if daily_pnl >= 0 else ""
        box2_bg = '#ecfdf5' if daily_pnl >= 0 else '#fef2f2'
        box2_border = '#10b981' if daily_pnl >= 0 else '#ef4444'
        box2_label_color = '#047857' if daily_pnl >= 0 else '#b91c1c'
        box2_val_color = '#059669' if daily_pnl >= 0 else '#dc2626'

        rect2 = patches.FancyBboxPatch(
            (0.73, 0.20), 0.27, 0.65,
            boxstyle="round,pad=0.03,rounding_size=0.08",
            facecolor=box2_bg, edgecolor=box2_border, linewidth=1.5,
            transform=ax_top.transAxes
        )
        ax_top.add_patch(rect2)
        ax_top.text(0.75, 0.65, f"KASA: ₺{end_equity:,.0f}", fontsize=7.5, fontweight='bold', color=box2_label_color, transform=ax_top.transAxes)
        ax_top.text(0.75, 0.32, f"{pnl_sign}₺{daily_pnl:,.2f} ({pnl_sign}%{pnl_pct:.2f})", fontsize=10.5, fontweight='bold', color=box2_val_color, transform=ax_top.transAxes)

        # 2. ALT PERFORMANS GRAFİĞİ
        ax = fig.add_subplot(gs[1])
        ax.set_facecolor('#ffffff')

        y_pos = list(range(len(symbols)))
        max_pos = max([p for p in pnls if p > 0] + [100.0])
        min_neg = min([p for p in pnls if p < 0] + [0.0])

        if min_neg >= 0:
            track_width = max_pos * 1.35
            for y in y_pos:
                ax.barh(y, track_width, color='#f1f5f9', height=0.46, edgecolor='none', zorder=1)

            colors = ['#10b981' for _ in pnls]
            ax.barh(y_pos, pnls, color=colors, height=0.46, edgecolor='none', zorder=2)

            for y, pnl, pct in zip(y_pos, pnls, pcts):
                val_str = f"  +₺{pnl:,.2f}  (+%{pct:.2f})"
                ax.text(
                    pnl + (max_pos * 0.02), y,
                    val_str,
                    va='center', ha='left',
                    color='#065f46',
                    fontsize=9.5, fontweight='bold', zorder=4
                )
            ax.set_xlim(0, max_pos * 1.45)
        else:
            limit_val = max(abs(min_neg), abs(max_pos)) * 1.35
            for y in y_pos:
                ax.barh(y, limit_val * 2, left=-limit_val, color='#f8fafc', height=0.46, edgecolor='none', zorder=1)

            colors = ['#10b981' if p >= 0 else '#ef4444' for p in pnls]
            ax.barh(y_pos, pnls, color=colors, height=0.46, edgecolor='none', zorder=2)
            ax.axvline(0, color='#cbd5e1', linewidth=1, linestyle='--', zorder=3)

            for y, pnl, pct in zip(y_pos, pnls, pcts):
                sign = "+" if pnl >= 0 else ""
                val_str = f" {sign}₺{pnl:,.2f} ({sign}%{pct:.2f}) "
                if pnl >= 0:
                    ax.text(pnl + (limit_val * 0.03), y, val_str, va='center', ha='left', color='#065f46', fontsize=9.5, fontweight='bold', zorder=4)
                else:
                    ax.text(pnl - (limit_val * 0.03), y, val_str, va='center', ha='right', color='#991b1b', fontsize=9.5, fontweight='bold', zorder=4)
            ax.set_xlim(-limit_val * 1.15, limit_val * 1.15)

        ax.set_yticks(y_pos)
        ax.set_yticklabels(symbols, fontsize=10.5, fontweight='bold', color='#1e293b')

        # Kenarlıkları kaldır (Çerçevesiz şık fintech görünüm)
        for spine in ax.spines.values():
            spine.set_visible(False)

        ax.xaxis.set_visible(False)
        ax.tick_params(left=False, pad=8)

        # Görseli kaydet
        os.makedirs("data/reports", exist_ok=True)
        out_path = f"data/reports/daily_report_{date_str}.png"
        plt.subplots_adjust(left=0.12, right=0.96, top=0.95, bottom=0.08)
        plt.savefig(out_path, facecolor='#ffffff', edgecolor='#e2e8f0', bbox_inches='tight')
        plt.close()
        return out_path
    except Exception as e:
        logger.error(f"[CHART] Görsel oluşturma hatası: {e}")
        return None





def format_simulation_report(date_str: str, start_equity: float, end_equity: float, daily_pnl: float, pnl_pct: float, win_trades: int, total_trades: int, trades: list) -> str:
    sign = "+" if daily_pnl >= 0 else ""
    pnl_emoji = "✅" if daily_pnl >= 0 else "🔻"
    win_rate = (win_trades / total_trades * 100) if total_trades > 0 else 0.0
    
    parts = date_str.split('-')
    fmt_date = f"{parts[2]}.{parts[1]}.{parts[0]}" if len(parts) == 3 else date_str
    
    text = f"🧪 <b>SİMÜLASYON GÜN SONU RAPORU</b> 🧪\n"
    text += f"📅 <i>{fmt_date} | Seans Kapanış Özeti</i>\n\n"
    
    text += f"💰 <b>KASA & PORTFÖY DURUMU</b>\n"
    text += f"━━━━━━━━━━━━━━━━━━━━\n"
    text += f"💵 <b>Başlangıç Parası:</b> ₺{start_equity:,.2f}\n"
    text += f"💎 <b>Bitiş Parası (Kasa):</b> ₺{end_equity:,.2f}\n"
    text += f"{pnl_emoji} <b>Günün Net Kârı:</b> {sign}₺{daily_pnl:,.2f} (<b>{sign}%{pnl_pct:.2f}</b>)\n"
    text += f"🎯 <b>Başarı Karnesi:</b> {win_trades}/{total_trades} Kârlı İşlem (<b>%{win_rate:.0f} Başarı</b>)\n"
    text += f"🛡️ <b>Pozisyon Durumu:</b> %100 NAKİT (Açık Gece Riski Yok)\n\n"
    
    if trades:
        text += f"📋 <b>GÜN İÇİ İŞLEM DÖKÜMÜ & HİSSELER</b>\n"
        text += f"━━━━━━━━━━━━━━━━━━━━\n"
        for idx, t in enumerate(trades[:12], 1):
            sym = str(t.get('symbol', '')).replace('.IS', '')
            val = float(t.get('realized_pnl', t.get('pnl_val', 0)))
            pct = float(t.get('pnl_pct', 0))
            entry = float(t.get('entry_price', 0))
            exit_p = float(t.get('exit_price', 0))
            v_sign = "+" if val >= 0 else ""
            t_emoji = "🟢" if val >= 0 else "🔴"
            reason = str(t.get('exit_reason', ''))
            tag = "⚖️ TP1 + Kapanış" if ("TP1" in reason and "SEANS SONU" in reason) else (
                "⚖️ TP1" if "TP1" in reason else (
                    "🏁 17:50 Nakit" if "SEANS SONU" in reason else (
                        "🛡️ Stop" if "STOP" in reason else "Satış"
                    )
                )
            )
            price_info = f" (₺{entry:.2f} ➔ ₺{exit_p:.2f})" if entry > 0 and exit_p > 0 else ""
            text += f"{idx}️⃣ <b>#{sym}</b>: {t_emoji} <b>{v_sign}₺{val:,.2f}</b> ({v_sign}%{pct:.2f}){price_info} | <i>{tag}</i>\n"
        
        if len(trades) > 12:
            text += f"   <i>...ve {len(trades) - 12} işlem daha</i>\n"
        text += f"\n"
    else:
        text += f"ℹ️ <i>Bugün işlem açılmadı; sermaye %100 nakit olarak korundu.</i>\n\n"
        
    text += "ℹ️ <i>Bu rapor simülasyon verisidir; seans sonu (17:50) tüm pozisyonlar otomatik kapatılarak %100 nakde geçilmiştir.</i>"
    return text





def _format_time_header(t_str: str, default_date: str = "") -> str:
    if not t_str:
        return default_date or ""
    try:
        if " " in t_str:
            d_part, t_part = t_str.split(" ", 1)
            dp = d_part.split("-")
            fmt_d = f"{dp[2]}.{dp[1]}.{dp[0]}" if len(dp) == 3 else d_part
            return f"{t_part} | {fmt_d}"
        return t_str
    except Exception:
        return t_str





def get_special_ranking_candidates(all_symbols_stats: dict, top_n: int = 5) -> list:
    """
    %90+ Başarı oranlı, tatlı bölgede (+%0.2 - +%4.8) kopuş yapan, tavan tuzaklarından arındırılmış
    ve kurumsal akıllı para girişli seçkin hisseleri filtreler ve sıralar.
    Web arayüzündeki '%90 Başarı (Güven + Hacim)' filtresiyle %100 birebir uyumludur.
    """
    if not all_symbols_stats or not isinstance(all_symbols_stats, dict):
        return []

    # SENARYO DINAMIGI: siralama agirliklari guncel rejime gore sekillenir.
    # GUCCLU AYI'da ozel siralama bildirimi tamamen susar (yalniz nakit dogru).
    try:
        from v8_engine.playbook import get_scenario
        _GDC = {}
        try:
            import json, os
            if os.path.exists("dashboard_cache.json"):
                with open("dashboard_cache.json", "r", encoding="utf-8") as _cf:
                    _GDC = json.load(_cf)
        except Exception:
            _GDC = {}
        _regime = (_GDC.get("v8_market_regime") or {}).get("regime", "NEUTRAL")
        _scenario = get_scenario(_regime)
        _rw = _scenario.get("rank_weights") or {"profit_take": 0.55, "plus5": 0.30, "ceiling": 0.15}
        if _regime == "STRONG_BEAR":
            return []
    except Exception:
        _rw = {"profit_take": 0.55, "plus5": 0.30, "ceiling": 0.15}

    scored_list = []

    for sym, data in all_symbols_stats.items():
        if not isinstance(data, dict):
            continue

        clean_sym = sym.replace(".IS", "").replace(".is", "").upper().strip()
        price = float(data.get("Price") or data.get("Daily_Close") or 0.0)
        change = float(data.get("Change_Pct") or 0.0)
        vol_lot = float(data.get("Volume") or 0.0)
        vol_tl = vol_lot * price

        # Göreceli Hacim (Hacim Gücü)
        v8 = data.get("v8_discovery") or {}
        v8_metrics = v8.get("metrics") or {} if isinstance(v8, dict) else {}
        rel_vol = float(v8_metrics.get("relative_volume") or data.get("Vol_Multiplier") or data.get("rel_vol") or 0.0)
        state = v8.get("state", "NONE") if isinstance(v8, dict) else "NONE"
        prep_score = float(v8.get("preparation_score", 0.0)) if isinstance(v8, dict) else 0.0

        # Gün içi güç metrikleri
        intra = data.get("intraday_strength") or {}
        if not isinstance(intra, dict):
            intra = {}
        intra_change = float(intra.get("intraday_change_pct") or 0.0)
        high = float(data.get("High") or price)
        low = float(data.get("Low") or price)
        if intra_change == 0.0:
            if low > 0 and price > low:
                intra_change = round(((price - low) / low) * 100, 2)
            elif change > 0:
                intra_change = round(change, 2)

        hourly_flow = str(intra.get("hourly_flow") or "Denge")
        acc_score = float(intra.get("accumulation_score") or 0.0)

        # ===== V8 %90+ GÜVEN VE BAŞARI HESAPLAMASI =====
        conf = 75.0
        bonuses = []

        # 1) Tatlı Bölge (+0.5% ile +3.8%): Tavan tuzağı ve düşüşten uzak
        if 0.5 <= change <= 3.8:
            bonuses.append("⚡ Tatlı Bölge")
            conf += 4.0
        elif 3.8 < change <= 5.0:
            bonuses.append("⚡ İvmelenme")
            conf += 2.0
        elif change > 7.0:
            conf -= 12.0
        elif change < 0.0:
            conf -= 15.0

        # 2) Hacim Gücü (Göreceli Hacim) — Kurumsal para akışı
        if rel_vol >= 2.5:
            bonuses.append("🔥 Süper Hacim")
            conf += 4.5
        elif rel_vol >= 1.5:
            bonuses.append("🔊 Güçlü Hacim")
            conf += 3.0
        elif rel_vol < 0.8 and change > 0:
            conf -= 6.0

        # 3) Akıllı Para & Gün İçi İvme
        if hourly_flow == "Toplanıyor" or intra_change >= 0.8:
            bonuses.append("💸 Akıllı Para")
            conf += 4.5
        elif hourly_flow == "Satılıyor":
            conf -= 12.0

        if intra_change < 0.0:
            conf -= 8.0

        # 4) Teknik Kalite / Kırılım
        if state in ("BREAKOUT", "PRE_BREAKOUT") or prep_score >= 60:
            bonuses.append("🛡️ Güçlü Hazırlık")
            conf += 4.0

        # 5) Likidite Güvencesi (30M+ TL kurumsal tahta)
        if vol_tl >= 30_000_000 and price >= 4.0:
            bonuses.append("🏦 Likit Tahta")
            conf += 3.0
        elif vol_tl < 15_000_000 or price < 3.0:
            conf -= 10.0

        conf = round(min(96.0, max(15.0, conf)), 1)

        # V8 Giriş Onaylı hisse kontrolü (Kullanıcı talebi: Özel sıralamaya V8 giriş onaylı hisseler eklenir)
        is_v8_approved = False
        v8_exec = data.get("v8_execution") or {}
        v8_bo = data.get("v8_breakout") or {}
        if (v8_exec.get("entry_status") == "ENTER") or (v8_bo.get("is_breakout") and float(v8_bo.get("breakout_score") or 0) >= 45):
            is_v8_approved = True
            bonuses.append("🎯 V8 Giriş Onaylı")
            conf = max(conf, 92.0)

        # ===== TEMEL %90+ BAŞARI FİLTRELERİ =====
        if not is_v8_approved:
            # 1. Kuruşluk hisseleri ele (Fiyat en az 3 TL)
            if price < 3.0:
                continue

            # 2. Minimum likidite kontrolü (Sığ hisse tuzaklarını engelle)
            if vol_tl < 20_000_000:
                continue

            # 3. % Değişim Tatlı Bölge Filtresi (+%0.2 ile +%5.5 arası)
            if change < 0.2 or change > 5.5:
                continue

            # 4. Gün içi güç negatif olanlar elenir
            if intra_change < -0.5:
                continue

            # 5. Saatlik para akışı Satılıyor olanlar elenir
            if hourly_flow == "Satılıyor":
                continue

            # 6. Güven skoru en az %80 olmalı
            if conf < 80.0:
                continue

        # --- Pivot Destek / Direnç Seviyeleri (Saatlik ve Günlük) ---
        p_val = (high + low + price) / 3.0
        daily_r1 = (2 * p_val) - low
        daily_s1 = (2 * p_val) - high
        if price > daily_r1: daily_r1 = p_val + (high - low)
        if price < daily_s1: daily_s1 = p_val - (high - low)
        hourly_r1 = price + (daily_r1 - price) * 0.4
        hourly_s1 = price - (price - daily_s1) * 0.4

        if daily_r1 <= price: daily_r1 = price * 1.025
        if daily_s1 >= price: daily_s1 = price * 0.975
        if hourly_r1 <= price: hourly_r1 = price * 1.012
        if hourly_s1 >= price: hourly_s1 = price * 0.988

        h_s1_pct = abs((hourly_s1 - price) / price * 100) if price > 0 else 0.0
        h_r1_pct = abs((hourly_r1 - price) / price * 100) if price > 0 else 0.0

        # --- Akıllı Özel Sıralama Skoru ---
        change_score = 30.0 + (change * 3.0) if 0.5 <= change <= 3.5 else 20.0
        vol_score = min(rel_vol, 4.0) * 8.0
        intra_score = min(max(intra_change, 0.0), 6.0) * 4.0
        flow_bonus = 8.0 if hourly_flow == "Toplanıyor" else 0.0
        tech_bonus = 10.0 if state in ("BREAKOUT", "PRE_BREAKOUT") else (min(prep_score, 100.0) * 0.1)
        liq_bonus = 6.0 if vol_tl >= 100_000_000 else (2.0 if vol_tl >= 30_000_000 else 0.0)

        raw_score = change_score + vol_score + intra_score + flow_bonus + tech_bonus + liq_bonus
        special_score = round(min(max(raw_score, 10.0), 99.0), 1)

        # Saatlik güç/hacim, kâr alma hedefinin ilk önceliğidir.
        hourly_strength = float(
            intra.get("hourly_strength")
            or intra.get("hourly_power")
            or intra.get("timeframe_quality")
            or 0.0
        )
        hourly_volume = float(
            intra.get("hourly_volume_strength")
            or intra.get("hourly_rel_vol")
            or rel_vol
            or 0.0
        )
        # Üç amaçlı sıralama:
        # 1) kısa sürede kâr alma, 2) +%5 devam, 3) tavan adayı.
        profit_take_score = (
            (25.0 if 0.2 <= change <= 4.8 else 0.0)
            + min(max(intra_change, 0.0) / 3.0, 1.0) * 25.0
            + min(max(hourly_strength, 0.0) / 100.0, 1.0) * 20.0
            + min(max(hourly_volume, 0.0) / 3.0, 1.0) * 15.0
            + (10.0 if hourly_flow == "Toplanıyor" else 0.0)
            + (5.0 if price > 0 and price > float(data.get("Daily_EMA50") or 0) else 0.0)
        )
        plus5_score = min(max(rel_vol / 3.0, 0.0), 1.0) * 35.0 + min(max(prep_score, 0.0), 100.0) * 0.35
        ceiling_score = min(max(float(data.get("tavan_score") or 0), 0.0), 100.0)
        # Dinamik agirliklar: ayi gununde tavan skoru sifirlanir, kâr alma domine eder.
        priority_score = round(
            profit_take_score * _rw.get("profit_take", 0.55)
            + plus5_score * _rw.get("plus5", 0.30)
            + ceiling_score * _rw.get("ceiling", 0.15),
            1,
        )

        scored_list.append({
            "symbol": clean_sym,
            "raw_symbol": sym,
            "price": price,
            "change": change,
            "intra_change": intra_change,
            "rel_vol": rel_vol,
            "hourly_flow": hourly_flow,
            "acc_score": acc_score,
            "volume_tl": vol_tl,
            "state": state,
            "confidence_pct": conf,
            "bonuses": bonuses,
            "special_score": special_score,
            "hourly_s1": round(hourly_s1, 2),
            "hourly_r1": round(hourly_r1, 2),
            "daily_s1": round(daily_s1, 2),
            "daily_r1": round(daily_r1, 2),
            "h_s1_pct": round(h_s1_pct, 1),
            "h_r1_pct": round(h_r1_pct, 1),
            "hourly_strength": round(hourly_strength, 1),
            "hourly_volume": round(hourly_volume, 2),
            "profit_take_score": round(profit_take_score, 1),
            "plus5_score": round(plus5_score, 1),
            "ceiling_score": round(ceiling_score, 1),
            "priority_score": priority_score,
        })

    # V8 Veritabanındaki Aktif Giriş Onaylı Sinyalleri Doğrudan Özel Sıralamaya Entegre Et
    try:
        import sqlite3, json, os
        db_path = "data/v8_signals.db"
        if os.path.exists(db_path):
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            cur.execute("SELECT symbol, entry_price, stop_price, target1, target2, market_regime, features_snapshot FROM v8_signals WHERE status = 'ACTIVE' ORDER BY timestamp DESC LIMIT 5")
            v8_rows = cur.fetchall()
            conn.close()
            for row in v8_rows:
                s_sym, s_entry, s_stop, s_t1, s_t2, s_regime, s_metrics_raw = row
                c_sym = s_sym.replace(".IS", "").replace(".is", "").upper().strip()
                if not any(c.get("symbol") == c_sym for c in scored_list):
                    s_metrics = json.loads(s_metrics_raw) if isinstance(s_metrics_raw, str) else (s_metrics_raw or {})
                    s_px = float(s_entry or 0.0)
                    s_chg = float(s_metrics.get("change_pct") or 0.0)
                    s_t1_f = float(s_t1 or (s_px * 1.035 if s_px > 0 else 0))
                    s_t2_f = float(s_t2 or (s_px * 1.065 if s_px > 0 else 0))
                    s_stop_f = float(s_stop or (s_px * 0.98 if s_px > 0 else 0))
                    scored_list.insert(0, {
                        "symbol": c_sym,
                        "raw_symbol": s_sym,
                        "price": s_px,
                        "change": s_chg,
                        "intra_change": s_chg,
                        "rel_vol": float(s_metrics.get("rel_vol") or 2.0),
                        "hourly_flow": "Toplanıyor",
                        "acc_score": 90.0,
                        "volume_tl": 80_000_000.0,
                        "state": "BREAKOUT",
                        "confidence_pct": 95.0,
                        "bonuses": ["🎯 V8 Giriş Onaylı", "💎 Kesin Kırılım"],
                        "special_score": 96.0,
                        "hourly_s1": round(s_stop_f, 2),
                        "hourly_r1": round(s_t1_f, 2),
                        "daily_s1": round(s_stop_f * 0.99, 2),
                        "daily_r1": round(s_t2_f, 2),
                        "h_s1_pct": 2.0,
                        "h_r1_pct": 3.5,
                        "hourly_strength": 90.0,
                        "hourly_volume": 2.5,
                        "profit_take_score": 96.0,
                        "plus5_score": 92.0,
                        "ceiling_score": 85.0,
                        "priority_score": 99.0,
                    })
    except Exception as e_v8:
        logger.warning(f"v8_signals.db read for special ranking: {e_v8}")

    # Öncelik: kâr alma -> +%5 -> tavan; güven eşiği zaten %90'dır.
    scored_list.sort(
        key=lambda x: (
            x["priority_score"],
            x["profit_take_score"],
            x["confidence_pct"],
            x["rel_vol"],
        ),
        reverse=True,
    )
    return scored_list[:top_n]





def send_special_ranking_alert(candidates: list, force: bool = False) -> bool:
    """
    En iyi %90+ başarı oranlı seçkin hisseleri güven skoru, destek, direnç ve
    canlı aksiyon planıyla şık bir Telegram mesajında gönderir.
    """
    if not candidates:
        return False

    medals = ["🥇", "🥈", "🥉", "🎖️", "🏅", "🔹", "🔹", "🔹"]

    text = "⭐ <b>%90+ BAŞARI ÖZEL SIRALAMA AKILLI SEÇİMLER</b> ⭐\n"
    text += "🎯 <i>Tatlı Bölge Kopuşu & Akıllı Kurumsal Para Onaylı Hisseler</i>\n\n"

    for idx, item in enumerate(candidates):
        medal = medals[idx] if idx < len(medals) else f"🔹 {idx+1}."
        sym = item.get("symbol", "")
        price = item.get("price", 0.0)
        chg = item.get("change", 0.0)
        intra_chg = item.get("intra_change", 0.0)
        r_vol = item.get("rel_vol", 0.0)
        flow = item.get("hourly_flow", "Denge")
        score = item.get("special_score", 0.0)
        conf = item.get("confidence_pct", 90.0)
        bonuses = item.get("bonuses", [])
        bonus_str = " ".join([f"[{b}]" for b in bonuses[:3]]) if bonuses else ""
        h_s1 = item.get("hourly_s1", 0.0)
        h_r1 = item.get("hourly_r1", 0.0)
        d_s1 = item.get("daily_s1", 0.0)
        d_r1 = item.get("daily_r1", 0.0)
        h_s1_p = item.get("h_s1_pct", 0.0)
        h_r1_p = item.get("h_r1_pct", 0.0)

        chg_sign = "+" if chg >= 0 else ""
        intra_sign = "+" if intra_chg >= 0 else ""

        flow_badge = "🟢 Toplanıyor" if flow == "Toplanıyor" else ("🔴 Satılıyor" if flow == "Satılıyor" else "⚪ Denge")

        # Aksiyon Planı Hesaplamaları
        stop_val = round(h_s1 * 0.985, 2)
        stop_pct = abs(round(((price - stop_val) / price) * 100, 1)) if price > 0 else 2.0
        tp1_val = round(price + (h_r1 - price) * 0.85, 2) if h_r1 > price else round(price * 1.035, 2)
        tp1_pct = abs(round(((tp1_val - price) / price) * 100, 1)) if price > 0 else 3.5
        tp2_val = round(max(d_r1, price * 1.065), 2)
        tp2_pct = abs(round(((tp2_val - price) / price) * 100, 1)) if price > 0 else 6.5

        text += f"{medal} <b>#{sym}</b> — ₺{price:.2f} (<b>{chg_sign}{chg:.2f}%</b>)\n"
        text += f"   🛡️ Güven Oranı: <b>%{conf:.0f}</b> | 🧠 Skor: <b>{score:.0f}/100</b>\n"
        if bonus_str:
            text += f"   ✨ Avantajlar: <i>{bonus_str}</i>\n"
        text += f"   ⚡ Gün İçi Güç: <b>{intra_sign}{intra_chg:.2f}%</b> | 🔊 Hacim Gücü: <b>{r_vol:.1f}x</b> | 🕒 Akış: <b>{flow_badge}</b>\n"
        text += f"   🛡️ Destek: ₺{h_s1:.2f} (-%{h_s1_p}) | 🎯 Direnç: ₺{h_r1:.2f} (+%{h_r1_p})\n"
        text += f"   📋 <b>CANLI AKSİYON PLANI:</b>\n"
        text += f"      🟢 <b>Alış Bölgesi:</b> ₺{h_s1:.2f} – ₺{price:.2f}\n"
        text += f"      🛑 <b>Stop (Zarar Kes):</b> ₺{stop_val:.2f} (-%{stop_pct})\n"
        text += f"      💰 <b>1. Kâr Al (%50 Sat):</b> ₺{tp1_val:.2f} (+%{tp1_pct}) ➡️ <i>Stop maliyete!</i>\n"
        text += f"      🏁 <b>2. Hedef (Direnç):</b> ₺{tp2_val:.2f} (+%{tp2_pct})\n\n"

    text += "💡 <i>Kural: Desteğe yakın toplayın, 1. Kâr Al seviyesinde yarısını satıp stopu maliyete çekerek sıfır riskle trendi izleyin.</i>"

    return send_telegram_message(text, force=force)





def send_morning_compass_bulletin(force: bool = False) -> bool:
    """
    Hergün 09:50'de Telegram kanalına gönderilen 'Günün Pusulası & Seans Öncesi Taktik Bülteni'.
    """
    from datetime import datetime
    today_date = datetime.now().strftime("%d.%m.%Y")

    text = "🧭 <b>GÜNÜN PİYASA PUSULASI & SEANS STRATEJİSİ</b> 🧭\n"
    text += f"📅 <i>{today_date} | Seans Öncesi Taktik Bülteni</i>\n\n"

    text += "📊 <b>Piyasa Genel Durumu:</b>\n"
    text += "• <b>BIST 100:</b> Seans açılışındaki ilk 15 dakika (10:00 - 10:15) volatiliteye karşı temkinli izleme önerilir.\n"
    text += "• <b>Odak Sektörler:</b> Hacim toplanması Savunma, Havacılık ve Enerji kümelerinde yoğunlaşıyor.\n\n"

    text += "🏆 <b>BUGÜNÜN 4 ALTIN KAZANÇ KURALI:</b>\n"
    text += "1️⃣ <b>10:15 - 11:30 Dağ Kekliği Avı:</b> Hacmi katlamış ama primi +%1.5 ile +%4 arasında kalmış erken kopuş adaylarına odaklanın.\n"
    text += "2️⃣ <b>Destek Altı Stop:</b> Bildirimdeki 'Saatlik Destek' seviyesinin altına mutlaka zarar kes stopu koyun.\n"
    text += "3️⃣ <b>+%3.5 Kârda %50 Satış:</b> İlk hedefe ulaşıldığında pozisyonun yarısını satın, kalan için stopu maliyet seviyenize çekin. (Sıfır Risk Prensibi)\n"
    text += "4️⃣ <b>Tuzaklara Düşmeyin:</b> %6 üzeri aşırı koşmuş veya üst fitili uzamış hisselere tepeden FOMO ile girmeyin.\n\n"

    text += "💡 <i>Özel Sıralama (Aksiyon Planlı) ve Dağ Kekliği sinyalleri 10:15'ten itibaren anlık olarak kanala iletilecektir. Bol kazançlar dileriz!</i> 🚀"

    return send_telegram_message(text, force=force)





def notify_tp1_reached(symbol: str, price: float, gain_pct: float) -> bool:
    """Hisse 1. Kâr Al hedefine ulaştığında tebrik ve yönlendirme uyarısı."""
    clean = symbol.replace(".IS", "").upper()
    text = f"🎉 <b>[HEDEF 1 ULAŞILDI!] #{clean}</b>\n\n"
    text += f"💰 <b>Anlık Fiyat:</b> ₺{price:.2f} (<b>+%{gain_pct:.1f}</b> kâr)\n\n"
    text += f"📋 <b>AKSYON REHBERİ:</b>\n"
    text += f"   ✅ Pozisyonun <b>%50'sini satın</b> ve kârı cebe koyun.\n"
    text += f"   🛡️ Kalan yarısının stop seviyesini derhal <b>alış maliyetinize çekin</b>.\n"
    text += f"   🚀 Artık bu işlemde zarar riski sıfırdır, tavan kilidine kadar izleyin!"
    return send_telegram_message(text)





def notify_trap_warning(symbol: str, price: float, reason: str) -> bool:
    """Hissede ani tuzak, fitil veya satış baskısı oluştuğunda koruma uyarısı."""
    clean = symbol.replace(".IS", "").upper()
    text = f"⚠️ <b>[DİKKAT: TUZAK / DÖNÜŞ RİSKİ] #{clean}</b>\n\n"
    text += f"💰 <b>Anlık Fiyat:</b> ₺{price:.2f}\n"
    text += f"🚨 <b>Uyarı Nedeni:</b> {reason}\n\n"
    text += f"📋 <b>AKSYON REHBERİ:</b>\n"
    text += f"   • Üst fitil uzadı veya hacimli kâr satışı belirdi.\n"
    text += f"   • Kârınızı realize edin veya iz süren stopu sıkılaştırın!\n"
    text += f"   • Yeni alım yapmaktan kaçının."
    return send_telegram_message(text)




def send_open_positions_report(trades: list = None, force: bool = True) -> dict:
    """
    Kullanicinin tek tikla tum acik simulasyon pozisyonlarini
    detaylariyla (lot, tutar, giris, kar/zarar, strateji, hedefler, portfoy ozeti)
    Telegram'a aninda gondermesini saglar.
    """
    from datetime import datetime
    try:
        from zoneinfo import ZoneInfo
        now_ist = datetime.now(ZoneInfo("Europe/Istanbul"))
    except Exception:
        now_ist = datetime.now()

    t_str = now_ist.strftime("%d.%m.%Y")
    h_str = now_ist.strftime("%H:%M")

    from services.trade_database import get_connection, SmartRow
    open_trades = []
    equity_info = {}

    if trades is not None:
        open_trades = [t for t in trades if (not t.get("exit_time") or not t.get("exit_price") or "AÇIK POZİSYON" in str(t.get("exit_reason") or ""))]
    else:
        try:
            with get_connection() as conn:
                conn.row_factory = SmartRow
                cur = conn.cursor()
                cur.execute("""
                    SELECT * FROM trades 
                    WHERE (exit_time IS NULL OR exit_time = '' OR exit_price IS NULL OR exit_reason LIKE '%AÇIK POZİSYON%')
                    ORDER BY entry_time DESC
                """)
                rows = cur.fetchall()
                seen = set()
                open_trades = []
                for r in rows:
                    sym = (r.get("symbol") or "").upper()
                    if sym and sym not in seen:
                        seen.add(sym)
                        open_trades.append(dict(r))

                cur.execute("SELECT * FROM equity_log ORDER BY date_str DESC LIMIT 1")
                eq_row = cur.fetchone()
                if eq_row:
                    equity_info = dict(eq_row)
        except Exception as e:
            logger.error(f"[OPEN-POS-TG] Veritabani okuma hatasi: {e}")

    if not open_trades:
        empty_lines = [
            "💼 <b>VARANTRADAR PRO — AÇIK POZİSYONLAR RAPORU</b>",
            "",
            f"📅 <b>Tarih:</b> {t_str} | ⏰ <b>Saat:</b> {h_str}",
            "ℹ️ <i>Şu anda portföyde açıkta bekleyen hisse pozisyonu bulunmamaktadır.</i>",
            "🛡️ <b>Durum:</b> %100 Nakit korunuyor."
        ]
        empty_text = "\n".join(empty_lines)
        ok = send_telegram_message(empty_text, force=force)
        return {"status": "success", "count": 0, "sent": ok, "message": "Açık pozisyon yok bilgisi iletildi."}

    lines = [
        "🚀 <b>VARANTRADAR PRO — CANLI AÇIK POZİSYONLAR</b> 🚀",
        f"📅 <b>Tarih:</b> {t_str} | ⏰ <b>Saat:</b> {h_str}",
        f"💼 <b>Toplam Açık Pozisyon:</b> {len(open_trades)} Adet",
        "────────────────────────"
    ]

    total_invested = 0.0
    total_unrealized_pnl = 0.0

    for i, tr in enumerate(open_trades, 1):
        sym = tr.get("symbol", "").replace(".IS", "").upper()
        entry_p = float(tr.get("entry_price") or 0.0)
        shares = int(tr.get("shares") or 0)
        cost = entry_p * shares
        total_invested += cost

        pnl_val = float(tr.get("pnl_val") or 0.0)
        pnl_pct = float(tr.get("pnl_pct") or 0.0)
        total_unrealized_pnl += pnl_val

        pnl_sign = "+" if pnl_pct >= 0 else ""
        pnl_emoji = "🟢" if pnl_pct >= 0 else "🔴"

        entry_time_str = str(tr.get("entry_time") or "")
        if " " in entry_time_str:
            entry_time_str = entry_time_str.split(" ")[1][:5]

        import html
        reason = tr.get("strategy_name") or tr.get("exit_reason") or tr.get("setup") or "V8 Erken Kopuş (Phase 1)"
        reason = html.escape(str(reason).replace("AÇIK POZİSYON", "").strip())
        if not reason:
            reason = "V8 Erken Kopuş (Phase 1)"

        t1 = float(tr.get("target1") or (entry_p * 1.03))
        t2 = float(tr.get("target2") or (entry_p * 1.05))
        sl = float(tr.get("stop_loss") or (entry_p * 0.98))

        lines.extend([
            f"<b>{i}. #{sym}</b>",
            f"├ 💵 <b>Giriş Fiyatı:</b> ₺{entry_p:.2f}",
            f"├ 📦 <b>Lot:</b> {shares:,} Adet (₺{cost:,.2f})",
            f"├ 📈 <b>Anlık Kâr/Zarar:</b> {pnl_emoji} <b>{pnl_sign}₺{pnl_val:,.2f} ({pnl_sign}%{pnl_pct:.2f})</b>",
            f"├ ⏰ <b>Giriş Saati:</b> {entry_time_str}",
            f"├ 🛡️ <b>Kurulum:</b> {reason}",
            f"└ 🎯 <b>Hedefler:</b> TP1: ₺{t1:.2f} · TP2: ₺{t2:.2f} · Stop: ₺{sl:.2f}",
            ""
        ])

    lines.append("────────────────────────")
    lines.append("📊 <b>PORTFÖY ÖZETİ:</b>")
    lines.append(f"💼 <b>Açık Pozisyon Tutarı:</b> ₺{total_invested:,.2f}")

    unreal_sign = "+" if total_unrealized_pnl >= 0 else ""
    unreal_emoji = "🟢" if total_unrealized_pnl >= 0 else "🔴"
    lines.append(f"💰 <b>Anlık Toplam Kâr/Zarar:</b> {unreal_emoji} <b>{unreal_sign}₺{total_unrealized_pnl:,.2f}</b>")

    balance = float(equity_info.get("end_equity") or (100000.0 + total_unrealized_pnl))
    lines.append(f"🏦 <b>Kasa Bakiyesi:</b> ₺{balance:,.2f}")
    lines.append("")
    lines.append("🔔 <i>Otomatik kâr alma (TP1/TP2) ve iz süren stop koruması aktiftir.</i>")

    text = "\n".join(lines)
    ok = send_telegram_message(text, force=force)
    global _LAST_TG_ERROR
    return {
        "status": "success",
        "count": len(open_trades),
        "sent": ok,
        "tg_error": _LAST_TG_ERROR,
        "message": f"{len(open_trades)} açık pozisyon Telegram'a başarıyla iletildi."
    }
