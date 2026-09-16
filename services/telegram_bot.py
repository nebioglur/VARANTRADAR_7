import requests
import json
import logging
import os
import time as _time
from typing import Optional
from config.settings import TELEGRAM_BOT_TOKEN as BOT_TOKEN, TELEGRAM_CHAT_ID as CHAT_ID

logger = logging.getLogger(__name__)

# ========== KIMLIK BILGISI COZUMLEME ==========
# Sıra: env degiskenleri -> kalici veritabani (live_settings) -> yerel sqlite settings.
# Render'da env tanimli olmasa bile uygulamadan kaydedilen ayarlar kullanilir.
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
                return row["value"]
            except (TypeError, KeyError, IndexError):
                return row[0] if isinstance(row, (tuple, list)) else None
    except Exception:
        pass
    try:
        from database.db_manager import DBManager
        return DBManager().get_setting(key)
    except Exception:
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


def send_telegram_message(text: str, parse_mode: str = "HTML") -> bool:
    """
    Belirlenen Chat ID'ye Telegram uzerinden mesaj gonderir.
    """
    bot_token, chat_id = get_telegram_credentials()
    if not bot_token or not chat_id:
        logger.error("Telegram ayarlari eksik (env + veritabani bos). Bildirim gonderilemedi! "
                     "Uygulamadan Telegram ayarlarini kaydedin.")
        return False

    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode
        }

        response = requests.post(url, json=payload, timeout=10)
        response_data = response.json()

        if response.status_code == 200 and response_data.get("ok"):
            logger.info(f"Telegram mesaji basariyla gonderildi: {text[:50]}...")
            return True
        else:
            logger.error(f"Telegram mesaji gonderilemedi! Hata: {response_data}")
            return False

    except Exception as e:
        logger.error(f"Telegram API cagrisi sirasinda hata olustu: {str(e)}")
        return False

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

def send_batch_vip_signals(vip_list: list) -> bool:
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
    
    return send_telegram_message(text)

def send_simulation_report(total_trades: int, total_profit: float, return_pct: float) -> bool:
    """
    Gun sonu simulasyon raporunu gonderir.
    """
    text = f"🧪 <b>Simulasyon Gun Sonu Raporu</b> 🧪\n\n"
    
    if total_profit > 0:
        text += f"✅ <b>Gunun Kari:</b> +{total_profit:,.2f} TL\n"
        text += f"📈 <b>Getiri Orani:</b> +%{return_pct:.2f}\n"
    else:
        text += f"❌ <b>Gunun Zarari:</b> {total_profit:,.2f} TL\n"
        text += f"📉 <b>Getiri Orani:</b> %{return_pct:.2f}\n"
        
    text += f"🛒 <b>Toplam Islem:</b> {total_trades} adet al-sat\n\n"
    text += f"<i>Sistem yarin icin tekrar taranmaya hazir.</i>"
    
    return send_telegram_message(text)


# ========== SESLI AL/SAT UYARILARI ==========
import os as _os

_ASSETS_DIR = _os.path.join(_os.path.dirname(__file__), "assets")


def send_voice_alert(alert_type: str, caption: str) -> bool:
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
        with open(path, "rb") as f:
            response = requests.post(
                url,
                data={"chat_id": chat_id, "caption": caption, "parse_mode": "HTML"},
                files={"audio": (_os.path.basename(path), f, "audio/mpeg")},
                timeout=20,
            )
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


def notify_sim_trade(symbol: str, action: str, price: float, pnl_pct: float = 0.0, reason: str = "", date_str: str = "", trade: dict = None) -> bool:
    import json, os
    from datetime import datetime
    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")
        
    cache_file = "data/sent_sim_alerts.json"
    cache = {}
    if os.path.exists(cache_file):
        try:
            with open(cache_file, "r", encoding="utf-8") as f_c:
                cache = json.load(f_c)
        except:
            pass
            
    if cache.get("date") != date_str:
        cache = {"date": date_str, "alerts": []}
        
    alert_key = f"{symbol}_{action}_{price:.2f}"
    if alert_key in cache["alerts"]:
        return True
        
    cache["alerts"].append(alert_key)
    try:
        with open(cache_file, "w", encoding="utf-8") as f_c:
            json.dump(cache, f_c)
    except:
        pass
        
    trade = trade or {}
    # Simülasyonun TÜM otomatik emirleri (AL, SAT, TP1, yeniden giriş, 17:50)
    # Telegram'a bildirilir. VIP puan filtresi YOK — canlı portföy işlemleri
    # buraya gelmez (yalnızca simulation_engine bu fonksiyonu çağırır).
    trade_score = trade.get("entry_score", trade.get("score", 0))
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
    
    if "AL" in action:
        text = "🤖 <b>SIMULASYON " + action + "</b>\n\n"
        text += "📈 <b>" + symbol + "</b> @ " + f"{price:.2f}" + " TL\n"
        text += "📦 <b>Lot Sayisi:</b> " + str(shares) + " Lot\n"
        text += "💰 <b>Toplam Tutar:</b> " + f"{total_val:.2f}" + " TL\n\n"
        text += "🎯 <b>Kar Al (TP):</b> " + f"{tp1:.2f}" + " TL (+%" + f"{tp_pct:.1f}" + ")\n"
        text += "🛑 <b>Stop Sat (SL):</b> " + f"{sl:.2f}" + " TL (-%" + f"{sl_pct:.1f}" + ")\n"
        text += _sr_text_block(symbol)
        text += f"🏆 <b>VIP Puanı:</b> {float(trade_score):.0f}/100\n"
        if entry_time:
            text += f"🕒 <b>Alış Saati:</b> {entry_time}\n"
        if strategy:
            text += f"🧠 <b>Strateji:</b> {strategy}\n"
        if risk_amount:
            text += f"⚠️ <b>Risk:</b> {float(risk_amount):.2f} TL\n"
        if regime:
            text += f"🌐 <b>Piyasa Rejimi:</b> {regime}\n"
        if checks:
            text += f"✅ <b>Kontroller:</b> {checks}\n"
        if reason:
            text += "\n💡 <b>Neden:</b> " + reason
        return send_telegram_message(text)
    else:
        emoji = "🟢" if pnl_pct >= 0 else "🔴"
        pnl_val = trade.get('pnl_val', 0)
        text = "🤖 <b>SIMULASYON " + action + "</b>\n\n"
        text += "📉 <b>" + symbol + "</b> @ " + f"{price:.2f}" + " TL\n"
        text += "📌 <b>Alış Fiyatı:</b> " + f"{float(entry):.2f}" + " TL\n"
        text += "📦 <b>Lot Sayisi:</b> " + str(shares) + " Lot\n"
        text += "💰 <b>Cikis Tutari:</b> " + f"{total_val:.2f}" + " TL\n\n"
        if tp1 and entry:
            text += "🎯 <b>Kar Al (TP):</b> " + f"{tp1:.2f}" + " TL (+%" + f"{tp_pct:.1f}" + ")\n"
        if sl and entry:
            text += "🛑 <b>Stop Sat (SL):</b> " + f"{sl:.2f}" + " TL (-%" + f"{sl_pct:.1f}" + ")\n"
        text += _sr_text_block(symbol)
        text += emoji + " <b>K/Z (Tutar):</b> " + f"{pnl_val:+.2f}" + " TL\n"
        text += emoji + " <b>K/Z (%):</b> %" + f"{pnl_pct:+.2f}" + "\n"
        text += f"🏆 <b>VIP Puanı:</b> {float(trade_score):.0f}/100\n"
        if entry_time:
            text += f"🕒 <b>Alış Saati:</b> {entry_time}\n"
        if exit_time:
            text += f"🕒 <b>Satış Saati:</b> {exit_time}\n"
        if strategy:
            text += f"🧠 <b>Strateji:</b> {strategy}\n"
        if regime:
            text += f"🌐 <b>Piyasa Rejimi:</b> {regime}\n"
        if reason:
            text += "\n💡 <b>Neden:</b> " + reason
        return send_telegram_message(text)
