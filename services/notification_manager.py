import os
import requests
from datetime import datetime
from database.db_manager import DBManager
from config.settings import TELEGRAM_BOT_TOKEN as DEFAULT_TOKEN, TELEGRAM_CHAT_ID as DEFAULT_CHAT_ID
from utils.logger import logger


VIP_SYMBOLS = [
    "AKBNK", "ALARK", "ASELS", "ASTOR", "BIMAS", "BRSAN", "DOAS", "EGEEN", 
    "EKGYO", "ENKAI", "EREGL", "FROTO", "GARAN", "GUBRF", "HEKTS", "ISCTR", "KCHOL", 
    "KONTR", "KOZAA", "KOZAL", "KRDMD", "ODAS", "OYAKC", "PETKM", "PGSUS", "SAHOL", 
    "SASA", "SISE", "TAVHL", "TCELL", "THYAO", "TOASO", "TUPRS", "VAKBN", "YKBNK"
]

def is_vip(symbol):
    clean = symbol.replace(".IS", "").upper()
    return clean in VIP_SYMBOLS


class NotificationManager:
    """
    VarantRadar Pro V7 - Profesyonel Bildirim ve Sinyal Merkezi
    Telegram Bot API üzerinden kullanıcılara anlık fiyatlı tavan, 1 saatlik ve 5 dakikalık sinyalleri iletir.
    """
    def __init__(self):
        self.db = DBManager()
        self._load_settings()

    def _load_settings(self):
        """Ayarları veritabanından, ortam değişkenlerinden veya varsayılanlardan yükler."""
        try:
            token = self.db.get_setting('telegram_token')
            chat_id = self.db.get_setting('telegram_chat_id')
            
            # Geçersiz veya placeholder ise fallback yap
            if not token or "BURAYA_" in str(token):
                token = os.environ.get("TELEGRAM_BOT_TOKEN") or os.environ.get("TELEGRAM_TOKEN") or DEFAULT_TOKEN
                if token and "BURAYA_" not in str(token):
                    self.db.save_setting('telegram_token', token)
                    
            if not chat_id or "BURAYA_" in str(chat_id):
                chat_id = os.environ.get("TELEGRAM_CHAT_ID") or DEFAULT_CHAT_ID
                if chat_id and "BURAYA_" not in str(chat_id):
                    self.db.save_setting('telegram_chat_id', chat_id)
                    
            self.telegram_token = str(token).strip() if token else None
            self.telegram_chat_id = str(chat_id).strip() if chat_id else None
        except Exception as e:
            logger.error(f"Telegram ayarları yüklenirken hata: {e}")
            self.telegram_token = DEFAULT_TOKEN
            self.telegram_chat_id = DEFAULT_CHAT_ID

    def send_telegram_message(self, message: str) -> bool:
        """Belirtilen Chat ID'ye veya virgülle ayrılmış ID'lere Telegram mesajı gönderir."""
        import time
        if not self.telegram_token or not self.telegram_chat_id or "BURAYA_" in str(self.telegram_token):
            self._load_settings()
            
        if not self.telegram_token or not self.telegram_chat_id:
            logger.warning("Telegram ayarları eksik. Bildirim gönderilemedi.")
            return False
            
        url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
        chat_ids = [cid.strip() for cid in str(self.telegram_chat_id).split(',') if cid.strip()]
        all_success = True
        
        for chat_id in chat_ids:
            payload = {
                "chat_id": chat_id,
                "text": message,
                "parse_mode": "HTML",
                "disable_web_page_preview": True
            }
            
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    response = requests.post(url, json=payload, timeout=10)
                    if response.status_code == 200:
                        self._log_alert(message, "TELEGRAM", f"SUCCESS_{chat_id}")
                        logger.info(f"Telegram bildirimi başarıyla iletildi (Chat ID: {chat_id})")
                        time.sleep(1) # Minimum 1 second delay
                        break
                    elif response.status_code == 429:
                        try:
                            error_data = response.json()
                            retry_after = error_data.get("parameters", {}).get("retry_after", 1)
                        except:
                            retry_after = 1
                        logger.warning(f"Telegram API Hatası: Too Many Requests: retry after {retry_after}")
                        time.sleep(retry_after)
                        if attempt == max_retries - 1:
                            self._log_alert(message, "TELEGRAM", f"FAILED_{chat_id}")
                            all_success = False
                    else:
                        logger.error(f"Telegram API Hatası ({chat_id}): {response.text}")
                        self._log_alert(message, "TELEGRAM", f"FAILED_{chat_id}")
                        all_success = False
                        time.sleep(1)
                        break
                except Exception as e:
                    logger.error(f"Telegram gönderim istisnası ({chat_id}): {e}")
                    self._log_alert(message, "TELEGRAM", f"ERROR_{chat_id}")
                    all_success = False
                    time.sleep(1)
                    break
                
        return all_success

    def send_system_startup_alert(self) -> bool:
        """Sunucu başladığında Telegram bağlantısının çalıştığını bildiren ilk mesaj. KULLANICI İSTEĞİ: İptal edildi."""
        return True
        now_str = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        msg = (
            f"🚀 <b>VARANTRADAR PRO AKTİF!</b> 🚀\n\n"
            f"🤖 <b>Sistem:</b> Canlı Tarama & Algoritmik Sinyal Motoru Devrede\n"
            f"📊 <b>Kapsam:</b> BIST Evreni, 1 Saatlik Fırsatlar, Tavan Radarı ve 5D RSI\n"
            f"⏱ <b>Başlangıç:</b> {now_str}\n\n"
            f"✨ <i>Piyasa fırsatları ve tavan alarmları anlık olarak iletilecektir.</i>"
        )
        return self.send_telegram_message(msg)

    def send_tavan_alert(self, symbol: str, score: int, reason: str, position: dict = None, extra: dict = None) -> bool:
        if not is_vip(symbol):
            return False
        
        clean_sym = symbol.replace(".IS", "").upper()
        msg = f"🚀 <b>VIP TAVAN ADAYI</b> 🚀

"
        msg += f"👑 <b>Hisse:</b> #{clean_sym}
"
        msg += f"🎯 <b>Puan:</b> {score}/100
"
        msg += f"📊 <b>Neden:</b> {reason}
"
        
        if extra and "Price" in extra:
            msg += f"💰 <b>Fiyat:</b> {float(extra['Price']):.2f}
"
            
        msg += f"
🤖 <i>VarantRadar VIP Motoru</i>"
        return self.send_telegram_message(msg)
def send_1h_opportunity_alert(self, opp: dict) -> bool:
        if not is_vip(opp.get('Symbol', '')): return False
        """1 Saatlik grafikte fırsat tespit edildiğinde atılacak mesaj."""
        return True # Kullanıcı isteği: Devre dışı bırakıldı
        clean_sym = opp.get("Symbol", "").replace(".IS", "").upper()
        raw_price = opp.get("Price")
        price_str = f"{float(raw_price):.2f}" if raw_price is not None else "-"
        
        chg_val = opp.get("Daily_Change_Pct") or opp.get("Change_Pct")
        if chg_val is not None:
            try:
                chg_num = float(chg_val)
                chg_sign = "+" if chg_num > 0 else ""
                chg_str = f"({chg_sign}%{chg_num:.2f})"
            except:
                chg_str = f"(%{chg_val})"
        else:
            chg_str = ""
            
        score_5 = opp.get("Score_5", 0)
        bars_ago = opp.get("Crossover_Bars_Ago", "?")
        ema_gap = opp.get("EMA_Gap_Pct", "-")
        rsi_val = opp.get("RSI_Val", "-")
        adx_val = opp.get("ADX_Val", "-")
        
        indicators = []
        if opp.get("EMA_Crossover_Bullish"):
            indicators.append(f"🔀 EMA 20/50 Kesişimi ({bars_ago} bar önce, Fark: %{ema_gap})")
        if opp.get("MACD_Match"):
            indicators.append("📈 MACD Pozitif AL Sinyali")
        if opp.get("RSI_Match"):
            indicators.append(f"📊 RSI > 50 Güçlü Bölge (RSI: {rsi_val})")
        if opp.get("ADX_Match"):
            indicators.append(f"💪 ADX Trend Gücü Yüksek (ADX: {adx_val})")
        if opp.get("MOM_Match"):
            indicators.append("⚡ Pozitif İvme / Momentum Artışı")

        msg = f"🔥 <b>1 SAATLİK TEKNİK FIRSAT</b> 🔥\n\n"
        msg += f"📌 <b>Hisse:</b> #{clean_sym}\n"
        msg += f"💰 <b>Anlık Fiyat:</b> ₺{price_str} {chg_str}\n"
        msg += f"⭐ <b>Teknik Filtre Skoru:</b> {score_5} / 5\n\n"
        msg += f"📋 <b>Tetiklenen İndikatörler:</b>\n"
        for ind in indicators:
            msg += f"  • {ind}\n"
            
        msg += f"\n🤖 <i>VarantRadar Pro 1 Saatlik Tarama</i>"
        return self.send_telegram_message(msg)

    def send_5m_rsi_alert(self, symbol: str, signal: str, rsi: float, price: float) -> bool:
        if not is_vip(symbol): return False
        """5 Dakikalık grafikte aşırı alım/satım veya RSI uyumsuzluğu tespit edildiğinde."""
        return True # Kullanıcı isteği: Devre dışı bırakıldı
        clean_sym = symbol.replace(".IS", "").upper()
        icon = "🟢" if signal == "AL" else "🔴"
        action_text = "GÜÇLÜ AL (Dipten Dönüş)" if signal == "AL" else "GÜÇLÜ SAT (Tepeden Çıkış)"
        price_str = f"{float(price):.2f}" if price else "-"
        rsi_str = f"{float(rsi):.1f}" if rsi else "-"
        
        msg = f"⚡ <b>5 Dk KISA VADE SCALP SİNYALİ</b> ⚡\n\n"
        msg += f"📌 <b>Hisse:</b> #{clean_sym}\n"
        msg += f"{icon} <b>Sinyal:</b> {action_text}\n"
        msg += f"💰 <b>Anlık Fiyat:</b> ₺{price_str}\n"
        msg += f"📈 <b>RSI (5m):</b> {rsi_str}\n\n"
        msg += f"⏱ <b>Zaman Dilimi:</b> 5 Dakikalık İntraday\n"
        msg += f"🤖 <i>VarantRadar Pro Hızlı Sinyal Motoru</i>"
        return self.send_telegram_message(msg)

    def send_radar_alert(self, symbol: str, score: int, level: str, reason: str, price: float = None, change_pct: float = None) -> bool:
        if not is_vip(symbol): return False
        
        clean_sym = symbol.replace(".IS", "").upper()
        msg = f"💎 <b>VIP RADAR FIRSATI</b> 💎

"
        msg += f"👑 <b>Hisse:</b> #{clean_sym}
"
        if price is not None:
            chg_str = f" (%+{change_pct:.2f})" if change_pct and change_pct > 0 else (f" (%{change_pct:.2f})" if change_pct else "")
            msg += f"💰 <b>Fiyat:</b> {price:.2f}{chg_str}
"
        msg += f"🎯 <b>Puan:</b> {score}/100
"
        msg += f"📊 <b>Seviye:</b> {level}
"
        msg += f"📝 <b>Neden:</b> {reason}

"
        msg += f"🤖 <i>VarantRadar VIP Motoru</i>"
        return self.send_telegram_message(msg)
def send_simulation_trade_alert(self, symbol: str, action: str, price: float, time_str: str, pnl_pct: float = None, reason: str = "") -> bool:
        import json, os
        from datetime import datetime
        cache_file = "data/sent_sim_trades.json"
        today = datetime.now().strftime("%Y-%m-%d")
        uid = f"{today}_{symbol}_{action}_{time_str}"
        sent_trades = []
        if os.path.exists(cache_file):
            try:
                with open(cache_file, "r") as f: sent_trades = json.load(f)
            except: pass
        if uid in sent_trades: return False
        
        clean_sym = symbol.replace(".IS", "").upper()
        
        if "AL" in action or action == "ENTER":
            icon = "🟢"
            title = "OTOMATIK ALIM EMRI"
        elif "KAR" in action or "TP" in action:
            icon = "🔵"
            title = "OTOMATIK KAR AL EMRI"
        elif "STOP" in action or "ZARAR" in action:
            icon = "🔴"
            title = "OTOMATIK STOP-LOSS EMRI"
        else:
            icon = "🟠"
            title = "OTOMATIK SATIS EMRI"
            
        msg = f"{icon} <b>SIMULASYON: {title}</b> {icon}

"
        msg += f"📌 <b>Hisse:</b> #{clean_sym}
"
        msg += f"⚡ <b>Islem Tipi:</b> <b>{action}</b>
"
        msg += f"💰 <b>Gerceklesen Fiyat:</b> <b>{float(price):.2f} TL</b>
"
        msg += f"⏱ <b>Emir Saati:</b> {time_str}
"
        
        if reason:
            msg += f"📝 <b>Strateji & Neden:</b> <i>{reason}</i>
"
            
        if pnl_pct is not None:
            pnl_icon = "🔥" if pnl_pct > 0 else "🩸"
            msg += f"{pnl_icon} <b>Kar/Zarar:</b> %{round(pnl_pct, 2)}
"
            
        msg += f"
🤖 <i>VarantRadar V8 AI Algoritmasi</i>"
            
        sent = self.send_telegram_message(msg)
        if sent:
            sent_trades.append(uid)
            try:
                os.makedirs("data", exist_ok=True)
                with open(cache_file, "w") as f: json.dump(sent_trades, f)
            except: pass
        return sent
def send_portfolio_alert(self, symbol: str, pnl_pct: float, action: str, price: float = None) -> bool:
        return False
        msg += f"🤖 <i>Lütfen sistemden kontrol ediniz.</i>"
        return self.send_telegram_message(msg)

    def _log_alert(self, message: str, channel: str, status: str):
        """Gönderilen alarmları veritabanına kaydeder."""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute('''INSERT INTO system_logs (level, message, created_at) 
                              VALUES (?, ?, ?)''',
                           (f"ALERT_{channel}_{status}", message[:120] + "...", datetime.now().isoformat()))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Alert loglama hatası: {e}")

    def update_settings(self, token: str, chat_id: str):
        """Telegram ayarlarını günceller."""
        try:
            token = str(token).strip() if token else ""
            chat_id = str(chat_id).strip() if chat_id else ""
            self.db.save_setting('telegram_token', token)
            self.db.save_setting('telegram_chat_id', chat_id)
            self.telegram_token = token
            self.telegram_chat_id = chat_id
            return True
        except Exception as e:
            logger.error(f"Ayarlar güncellenemedi: {e}")
            return False
