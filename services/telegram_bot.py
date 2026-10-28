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

        # DBManager ile de senkronize et
        try:
            from database.db_manager import DBManager
            db = DBManager()
            db.save_setting('telegram_token', str(token).strip())
            db.save_setting('telegram_chat_id', str(chat_id).strip())
        except Exception as e_db:
            logger.warning(f"DBManager telegram ayari senkronize edilemedi: {e_db}")

        get_telegram_credentials(force=True)
        logger.info("Telegram ayarlari kalici olarak kaydedildi.")
        return True
    except Exception as e:
        logger.error(f"Telegram ayarlari kaydedilemedi: {e}")
        return False


def send_telegram_message(text: str, parse_mode: str = "HTML") -> bool:
    """
    Belirlenen Chat ID'ye veya virgülle ayrılmış birden fazla Chat ID'ye Telegram mesajı gönderir.
    """
    bot_token, raw_chat_id = get_telegram_credentials()
    if not bot_token or not raw_chat_id:
        logger.error("Telegram ayarlari eksik (env + veritabani bos). Bildirim gonderilemedi! "
                     "Uygulamadan Telegram ayarlarini kaydedin.")
        return False

    chat_ids = [cid.strip() for cid in str(raw_chat_id).split(",") if cid.strip()]
    if not chat_ids:
        return False

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    any_success = False

    for cid in chat_ids:
        try:
            payload = {
                "chat_id": cid,
                "text": text,
                "parse_mode": parse_mode,
                "disable_web_page_preview": True
            }

            response = requests.post(url, json=payload, timeout=10)
            response_data = response.json()

            if response.status_code == 200 and response_data.get("ok"):
                logger.info(f"Telegram mesaji basariyla gonderildi ({cid}): {text[:50]}...")
                any_success = True
            else:
                logger.error(f"Telegram mesaji gonderilemedi ({cid})! Hata: {response_data}")
        except Exception as e:
            logger.error(f"Telegram API cagrisi sirasinda hata olustu ({cid}): {str(e)}")

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


def send_telegram_photo(photo_path: str, caption: str = "") -> bool:
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
                resp = requests.post(url, data=data, files=files, timeout=25)
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
    text += f"🎯 <b>Başarı Karnesi:</b> {win_trades}/{total_trades} Kârlı İşlem (<b>%{win_rate:.0f} Başarı</b>)\n\n"
    
    if trades:
        text += f"📋 <b>GÜN İÇİ İŞLEM DÖKÜMÜ</b>\n"
        text += f"━━━━━━━━━━━━━━━━━━━━\n"
        for idx, t in enumerate(trades[:6], 1):
            sym = str(t.get('symbol', '')).replace('.IS', '')
            val = float(t.get('pnl_val', 0))
            pct = float(t.get('pnl_pct', 0))
            v_sign = "+" if val >= 0 else ""
            t_emoji = "🟢" if val >= 0 else "🔴"
            reason = str(t.get('exit_reason', ''))
            tag = "⚖️ TP1" if "TP1" in reason else ("🏁 Kapanış" if "SEANS SONU" in reason else "🛡️ Kâr Koruma")
            text += f"{idx}️⃣ <b>#{sym}</b>: {t_emoji} <b>{v_sign}₺{val:,.2f}</b> ({v_sign}%{pct:.2f}) | <i>{tag}</i>\n"
        
        if len(trades) > 6:
            text += f"   <i>...ve {len(trades) - 6} işlem daha</i>\n"
        text += f"\n"
        
    text += f"🏆 <i>Tüm işlemler kurallara uygun icra edildi. Sistem yarın için taranmaya hazır!</i>"
    return text


def send_simulation_report(total_trades: int = 0, total_profit: float = 0.0, return_pct: float = 0.0, date_str: str = "", owner: str = None) -> bool:
    """
    Kapsamlı gün sonu simülasyon raporunu görsel grafik, başlangıç/bitiş parası ve
    işlem dökümüyle birlikte gönderir. Mükerrer gönderimi veritabanı kilidiyle kesin engeller.
    """
    from datetime import datetime
    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")
    owner = owner or os.environ.get('ADMIN_OWNER', 'local:nebioglur')
    
    # 1. MÜKERRER MESAJ KİLİDİ (Atomik Veritabanı Engeli)
    # Server restartı, çoklu thread veya worker tekrarlarında ikinci kez gitmesini KESİN engeller!
    dedup_key = f"DAILY_REPORT_{date_str}_{owner}"
    if not claim_telegram_alert(dedup_key):
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
            cur.execute("SELECT * FROM equity_log WHERE date_str=? AND owner=?", (date_str, owner))
            eq = cur.fetchone()
            if eq:
                start_equity = float(eq['start_equity']) if eq['start_equity'] else 100000.0
                end_equity = float(eq['end_equity']) if eq['end_equity'] else (start_equity + daily_pnl)
                daily_pnl = float(eq['daily_pnl']) if eq['daily_pnl'] is not None else daily_pnl
                win_trades = int(eq['win_trades']) if eq['win_trades'] is not None else 0
                t_count = int(eq['total_trades']) if eq['total_trades'] is not None else total_trades
                pnl_pct = (daily_pnl / start_equity * 100) if start_equity > 0 else 0.0

            cur.execute("SELECT * FROM trades WHERE date_str=? AND owner=? ORDER BY pnl_val DESC", (date_str, owner))
            trades_list = [dict(r) for r in cur.fetchall()]
            if not t_count:
                t_count = len(trades_list)
            if not win_trades:
                win_trades = sum(1 for t in trades_list if float(t.get('pnl_val', 0)) > 0)
    except Exception as db_err:
        logger.error(f"[TG-REPORT] DB veri çekme hatası: {db_err}")

    # 3. Zengin Metin Raporunu Oluştur
    caption = format_simulation_report(date_str, start_equity, end_equity, daily_pnl, pnl_pct, win_trades, t_count, trades_list)

    # 4. Performans Grafik Kartını Üret
    photo_path = generate_daily_report_chart(date_str, start_equity, end_equity, daily_pnl, pnl_pct, trades_list)

    # 5. Gönder (Fotoğraf + Başlık metni, hata olursa sadece metin)
    sent = False
    if photo_path and os.path.exists(photo_path):
        sent = send_telegram_photo(photo_path, caption)
        
    if not sent:
        sent = send_telegram_message(caption)
        
    return sent


# ========== SESLI AL/SAT UYARILARI ==========
import os as _os

_ASSETS_DIR = _os.path.join(_os.path.dirname(__file__), "assets")


def send_voice_alert(alert_type: str, caption: str) -> bool:
    """Sesli uyari gonderir: buy_alert / sell_alert mp3 + mesaj.
    Ses dosyasi yoksa duz mesaj fallback."""
    bot_token, raw_chat_id = get_telegram_credentials()
    if not bot_token or not raw_chat_id:
        return send_telegram_message(caption)

    file_map = {
        "buy": _os.path.join(_ASSETS_DIR, "buy_alert.mp3"),
        "sell": _os.path.join(_ASSETS_DIR, "sell_alert.mp3"),
    }
    path = file_map.get(alert_type)
    if not path or not _os.path.exists(path):
        return send_telegram_message(caption)

    chat_ids = [cid.strip() for cid in str(raw_chat_id).split(",") if cid.strip()]
    if not chat_ids:
        return False

    url = f"https://api.telegram.org/bot{bot_token}/sendAudio"
    any_success = False

    for cid in chat_ids:
        try:
            with open(path, "rb") as f:
                response = requests.post(
                    url,
                    data={"chat_id": cid, "caption": caption, "parse_mode": "HTML"},
                    files={"audio": (_os.path.basename(path), f, "audio/mpeg")},
                    timeout=20,
                )
            data = response.json()
            if response.status_code == 200 and data.get("ok"):
                logger.info(f"Telegram sesli uyari gonderildi ({alert_type}, {cid}): {caption[:50]}")
                any_success = True
            else:
                logger.error(f"Telegram sesli uyari hatasi ({cid}): {data}")
        except Exception as e:
            logger.error(f"Telegram sesli uyari exception ({cid}): {e}")

    return any_success


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


def _sr_text_block(symbol: str) -> str:
    """Bildirim mesajlari icin temiz destek/direnc bolumu."""
    sr = get_support_resistance(symbol)
    if not sr:
        return ""
    s1, s2, r1, r2, piv = sr
    return (
        f"🛡️ <b>Destek / Direnç:</b> ₺{s1:.2f} / ₺{r1:.2f}\n"
        f"⚖️ <b>Pivot Seviyesi:</b> ₺{piv:.2f}\n"
    )


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
        # KULLANICI ISTEGI: gecmis gun kapanislari dahil TUM trade olaylari
        # Telegram'a gider (eskisi gibi). Yalnizca gelecekteki bozuk/zaman
        # tasmali olaylar engellenir; dedup zaten mukerrer mesaji onler.
        if event_dt > local_now + timedelta(minutes=5):
            return True
    except (TypeError, ValueError):
        logger.warning("Simulasyon Telegram olayi icin zaman okunamadi: %s", event_time)
        return False

    identity = "|".join((date_str, symbol, action, entry_time, event_time))
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

    trade_score = trade.get("entry_score", trade.get("score", 0))

    def _send_once(message: str) -> bool:
        sent = send_telegram_message(message)
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
        text = f"🟢 <b>SİMÜLASYON AL EMRİ</b> 🟢\n"
        text += f"⏰ <b>Alış Saati:</b> <code>{display_time}</code>\n"
        text += "━━━━━━━━━━━━━━━━━━━━\n"
        text += f"📌 <b>HİSSE:</b> <b>#{clean_sym}</b>\n"
        text += f"💵 <b>Alış Fiyatı:</b> ₺{price:.2f}\n"
        text += f"📦 <b>Pozisyon:</b> {shares} Lot  (₺{total_val:,.2f})\n"
        text += f"🏆 <b>Sistem Puanı:</b> {float(trade_score):.0f}/100 (Elit Seçim)\n\n"
        
        text += "🎯 <b>HEDEFLER VE RİSK PLANI</b>\n"
        text += "━━━━━━━━━━━━━━━━━━━━\n"
        text += f"💰 <b>1. Kâr Al (TP1):</b> ₺{tp1:.2f} (<b>+%2.2</b>) ➡️ <i>Yarısı satılır</i>\n"
        text += f"🛑 <b>Zarar Kes (Stop):</b> ₺{sl:.2f} (<b>-%2.5</b>)\n"
        text += f"🛡️ <b>Sıfır Risk:</b> +%1.8 kârda stop maliyet üstüne taşınır\n\n"
        
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
    else:
        emoji = "🟢" if pnl_pct >= 0 else "🔴"
        pnl_val = trade.get('pnl_val', 0)
        display_exit_time = _format_time_header(exit_time, date_str)
        display_entry_time = _format_time_header(entry_time, "")
        
        text = f"🔴 <b>SİMÜLASYON SAT EMRİ</b> 🔴\n"
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

def get_special_ranking_candidates(all_symbols_stats: dict, top_n: int = 5) -> list:
    """
    En hacim gücü yüksek, gün içi güç yüksek ve % değişimi az (henüz fiyatlanmamış)
    akıllı hisse seçimlerini hesaplar ve sıralar.
    Web arayüzündeki 'Özel Sıralama' algoritmasıyla birebir uyumludur.
    """
    if not all_symbols_stats or not isinstance(all_symbols_stats, dict):
        return []

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

        # Temel Filtreler:
        # 1. Fiyat geçerli olmalı (Kuruşluk hisseleri ele)
        if price < 3.0:
            continue

        # 2. Minimum likidite kontrolü (Sığ hisse ve tahta yapıcı tuzaklarını engeller)
        if vol_tl < 15_000_000:
            continue

        # 3. % Değişim filtresi (Düşen eksi hisseler ve aşırı primli tavan kovalama elenir)
        if change < -0.8 or change > 5.5:
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

        # --- Akıllı Özel Sıralama Skoru (Kopuş Tatlı Bölgesi & Hacim Patlaması) ---
        # 1) Tatlı Bölge Değişimi: +0.5% ile +3.5% arası en ideal kopuş başlangıcı
        if 0.5 <= change <= 3.5:
            change_score = 30.0 + (change * 3.0)
        elif 3.5 < change <= 5.0:
            change_score = 30.0 - ((change - 3.5) * 6.0)
        elif change > 5.0:
            change_score = 15.0 - ((change - 5.0) * 8.0)
        elif 0.0 <= change < 0.5:
            change_score = 15.0 + (change * 10.0)
        else:
            change_score = -20.0 - (abs(change) * 12.0)

        # 2) Hacim gücü (Göreceli Hacim) — Kurumsal giriş teyidi
        vol_score = min(rel_vol, 4.0) * 8.0

        # 3) Gün içi güç (Dipten toparlanma)
        intra_score = min(max(intra_change, 0.0), 6.0) * 4.0

        # 4) Saatlik para akışı bonusu
        flow_bonus = 8.0 if hourly_flow == "Toplanıyor" else (0.0 if hourly_flow == "Denge" else -8.0)

        # 5) Teknik hazırlık (V8 Breakout) bonusu
        tech_bonus = 10.0 if state in ("BREAKOUT", "PRE_BREAKOUT") else (min(prep_score, 100.0) * 0.1)

        # 6) Likidite Bonusu: BIST kurumsal tahtalarına öncelik
        liq_bonus = 6.0 if vol_tl >= 100_000_000 else (2.0 if vol_tl >= 30_000_000 else -4.0)

        raw_score = change_score + vol_score + intra_score + flow_bonus + tech_bonus + liq_bonus
        special_score = round(min(max(raw_score, 10.0), 99.0), 1)

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
            "special_score": special_score,
            "hourly_s1": round(hourly_s1, 2),
            "hourly_r1": round(hourly_r1, 2),
            "daily_s1": round(daily_s1, 2),
            "daily_r1": round(daily_r1, 2),
            "h_s1_pct": round(h_s1_pct, 1),
            "h_r1_pct": round(h_r1_pct, 1),
        })

    # Sıralama: Özel puana göre en yüksekten düşüğe
    scored_list.sort(key=lambda x: (x["special_score"], x["rel_vol"], x["intra_change"]), reverse=True)
    return scored_list[:top_n]


def send_special_ranking_alert(candidates: list) -> bool:
    """
    En iyi özel sıralama adaylarını destek, direnç ve saatlik akış detaylarıyla
    tek bir şık Telegram mesajında gönderir.
    """
    if not candidates:
        return False

    medals = ["🥇", "🥈", "🥉", "🎖️", "🏅", "🔹", "🔹", "🔹"]

    text = "🌟 <b>ÖZEL SIRALAMA (AKILLI SEÇİM)</b> 🌟\n"
    text += "🎯 <i>Yüksek Hacim & Gün İçi Güç — Henüz Fiyatlanmamış Potansiyeller</i>\n\n"

    for idx, item in enumerate(candidates):
        medal = medals[idx] if idx < len(medals) else f"🔹 {idx+1}."
        sym = item.get("symbol", "")
        price = item.get("price", 0.0)
        chg = item.get("change", 0.0)
        intra_chg = item.get("intra_change", 0.0)
        r_vol = item.get("rel_vol", 0.0)
        flow = item.get("hourly_flow", "Denge")
        score = item.get("special_score", 0.0)
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
        text += f"   ⚡ Gün İçi Güç: <b>{intra_sign}{intra_chg:.2f}%</b> | 🔊 Hacim Gücü: <b>{r_vol:.1f}x</b>\n"
        text += f"   🕒 Saatlik Akış: <b>{flow_badge}</b> | 🧠 Özel Skor: <b>{score:.0f}/100</b>\n"
        text += f"   🛡️ Destek: ₺{h_s1:.2f} (-%{h_s1_p}) | 🎯 Direnç: ₺{h_r1:.2f} (+%{h_r1_p})\n"
        text += f"   📋 <b>CANLI AKSİYON PLANI:</b>\n"
        text += f"      🟢 <b>Alış Bölgesi:</b> ₺{h_s1:.2f} – ₺{price:.2f}\n"
        text += f"      🛑 <b>Stop (Zarar Kes):</b> ₺{stop_val:.2f} (-%{stop_pct})\n"
        text += f"      💰 <b>1. Kâr Al (%50 Sat):</b> ₺{tp1_val:.2f} (+%{tp1_pct}) ➡️ <i>Stop maliyete!</i>\n"
        text += f"      🏁 <b>2. Hedef (Direnç):</b> ₺{tp2_val:.2f} (+%{tp2_pct})\n\n"

    text += "💡 <i>Kural: Desteğe yakın toplayın, 1. Kâr Al seviyesinde yarısını satıp stopu maliyete çekerek sıfır riskle trendi izleyin.</i>"

    return send_telegram_message(text)


def send_morning_compass_bulletin() -> bool:
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

    return send_telegram_message(text)


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

