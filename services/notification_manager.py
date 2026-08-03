import requests
from datetime import datetime
from database.db_manager import DBManager
from utils.logger import logger

class NotificationManager:
    """
    VarantRadar Pro V7 - Bildirim ve Alarm Merkezi
    Telegram Bot API üzerinden kullanıcılara anlık sinyal ve portföy uyarıları gönderir.
    """
    def __init__(self):
        self.db = DBManager()
        self._load_settings()

    def _load_settings(self):
        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT setting_value FROM settings WHERE setting_key='telegram_token'")
            row = cursor.fetchone()
            self.telegram_token = row[0] if row else None
            
            cursor.execute("SELECT setting_value FROM settings WHERE setting_key='telegram_chat_id'")
            row = cursor.fetchone()
            self.telegram_chat_id = row[0] if row else None
        finally:
            conn.close()

    def send_telegram_message(self, message: str) -> bool:
        """Belirtilen Chat ID'ye veya ID'lere Telegram mesajı gönderir."""
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
                "parse_mode": "HTML"
            }
            
            try:
                response = requests.post(url, json=payload, timeout=5)
                if response.status_code == 200:
                    self._log_alert(message, "TELEGRAM", f"SUCCESS_{chat_id}")
                else:
                    logger.error(f"Telegram API Hatası ({chat_id}): {response.text}")
                    self._log_alert(message, "TELEGRAM", f"FAILED_{chat_id}")
                    all_success = False
            except Exception as e:
                logger.error(f"Telegram gönderim hatası ({chat_id}): {e}")
                self._log_alert(message, "TELEGRAM", f"ERROR_{chat_id}")
                all_success = False
                
        return all_success

    def send_radar_alert(self, symbol: str, score: int, level: str, reason: str):
        """Radar yeni bir fırsat bulduğunda tetiklenir."""
        msg = f"🚨 <b>YENİ RADAR FIRSATI</b> 🚨\n\n"
        msg += f"📌 <b>Hisse:</b> {symbol}\n"
        msg += f"⭐ <b>Puan:</b> {score}/100\n"
        msg += f"📊 <b>Seviye:</b> {level}\n"
        msg += f"💡 <b>Neden:</b> {reason}\n\n"
        msg += f"🤖 <i>VarantRadar Pro V7 Otomasyon Sistemi</i>"
        self.send_telegram_message(msg)

    def send_portfolio_alert(self, symbol: str, pnl_pct: float, action: str):
        """Stop veya Take Profit seviyesine gelindiğinde tetiklenir."""
        icon = "🟢" if pnl_pct > 0 else "🔴"
        msg = f"{icon} <b>PORTFÖY ALARMI</b> {icon}\n\n"
        msg += f"📌 <b>İşlem:</b> {action} {symbol}\n"
        msg += f"💰 <b>Kâr/Zarar:</b> %{round(pnl_pct, 2)}\n\n"
        msg += f"🤖 <i>Lütfen sistemden kontrol ediniz.</i>"
        self.send_telegram_message(msg)

    def send_tavan_alert(self, symbol: str, score: int, reason: str, position: dict = None, extra: dict = None):
        """Yüksek Tavan Olasılığı tespit edildiğinde profesyonel detaylı şablonla tetiklenir."""
        extra = extra or {}
        clean_sym = symbol.replace(".IS", "")
        tavan_price = extra.get("Ceiling_Price", position.get("TP2", "-") if position else "-")
        dist = extra.get("Distance_To_Ceiling_Pct", "-")
        vol_m = extra.get("Vol_Multiplier", "-")
        phase = extra.get("Phase_Badge", "TAVAN RADARI")
        chg = extra.get("Daily_Change_Pct", "-")
        candle_st = extra.get("Candle_Strength", "")
        trap = extra.get("Trap_Risk", False)
        v_rev = extra.get("V_Reversal", False)
        v_pow = extra.get("V_Power", 0.0)
        eta = extra.get("ETA", position.get("Projection", "-") if position else "-")
        domino_sec = extra.get("Domino_Sector")
        domino_peers = extra.get("Domino_Peers", [])
        warrant = extra.get("Warrant_Match")
        streak = extra.get("Streak_Potential")
        breakdown = extra.get("Breakdown_Warning")
        
        msg = f"🚀 <b>[{phase}] DAĞ KEKLİĞİ TAVAN RADARI</b> 🚀\n\n"
        msg += f"📌 <b>Hisse:</b> #{clean_sym}\n"
        msg += f"💰 <b>Anlık Fiyat:</b> ₺{extra.get('Price', position.get('Entry', '-') if position else '-')} (%{chg})\n"
        msg += f"🎯 <b>Tavan Hedefi:</b> ₺{tavan_price} (Kalan: %{dist})\n"
        msg += f"⭐ <b>AI Tavan Skoru:</b> {score}/100\n"
        msg += f"🔥 <b>Hacim Gücü:</b> {vol_m}x Katlama\n"
        msg += f"⏱ <b>Tahmini Tavan Saati (ETA):</b> {eta}\n"
        
        if streak:
            msg += f"🔗 <b>Tavan Zinciri:</b> {streak}\n"
            
        if v_rev:
            msg += f"⚡ <b>V-Dönüş Gücü:</b> Dipten +%{v_pow} Hızlı Sıçrama!\n"
            
        if candle_st:
            msg += f"🕯 <b>Mum Durumu:</b> {candle_st}\n"
            
        if trap:
            msg += f"⚠️ <b>UYARI:</b> Üst fitil uzun (Satış Baskısı / Tuzak Riski!)\n"
            
        if breakdown:
            msg += f"\n🚨 <b>ACİL UYARI:</b> {breakdown}\n"
            
        if domino_sec and domino_peers:
            peer_txt = ", ".join([f"#{p}" for p in domino_peers[:3]])
            msg += f"\n♟️ <b>Domino Etkisi ({domino_sec}):</b> Peşinden gelebilecek kardeşler: {peer_txt}\n"
            
        if warrant:
            msg += f"\n🎯 <b>VARANT ROKETİ EŞLEŞMESİ:</b>\n"
            msg += f"   • Dayanak: #{clean_sym} ➡️ Varant Grubu: <b>{warrant.get('Name')} ({warrant.get('Leverage')})</b>\n"
            msg += f"   • Potansiyel Getiri: <b>+%{warrant.get('Potential_Gain_Pct')}%</b>\n"
            
        if position:
            msg += f"\n🛡 <b>İz Süren Stop (SL):</b> ₺{position.get('SL', '-')}\n"
            msg += f"🎯 <b>İlk Kâr Al (TP1):</b> ₺{position.get('TP1', '-')}\n"
            msg += f"⚖️ <b>Risk/Kazanç (R:R):</b> 1:{position.get('RR', '-')}\n"
            
        msg += f"\n💡 <b>Teknik Özet:</b> {reason}\n"
        msg += f"\n🤖 <i>VarantRadar Pro V7 Otomasyon</i>"
        self.send_telegram_message(msg)

    def send_5m_rsi_alert(self, symbol: str, signal: str, rsi: float, price: float):
        """5 Dakikalık Kısa Vade RSI Kesişimi."""
        icon = "🟢" if signal == "AL" else "🔴"
        msg = f"⚡ <b>5 Dk KISA TRADE SİNYALİ</b> ⚡\n\n"
        msg += f"📌 <b>Hisse:</b> {symbol}\n"
        msg += f"{icon} <b>Sinyal Yönü:</b> {signal}\n"
        msg += f"💵 <b>Fiyat:</b> ₺{price}\n"
        msg += f"📈 <b>RSI(14):</b> {rsi}\n\n"
        msg += f"🤖 <i>VarantRadar Pro V7</i>"
        self.send_telegram_message(msg)

    def _log_alert(self, message: str, channel: str, status: str):
        """Gönderilen alarmları veritabanına kaydeder."""
        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('''INSERT INTO system_logs (level, message, created_at) 
                              VALUES (?, ?, ?)''',
                           (f"ALERT_{channel}_{status}", message[:100] + "...", datetime.now().isoformat()))
            conn.commit()
        except Exception as e:
            logger.error(f"Alert loglama hatası: {e}")
        finally:
            conn.close()

    def update_settings(self, token: str, chat_id: str):
        """Telegram ayarlarını günceller."""
        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()
            now = datetime.now().isoformat()
            
            # Upsert logic for token
            cursor.execute("INSERT OR REPLACE INTO settings (id, setting_key, setting_value, updated_at) VALUES ((SELECT id FROM settings WHERE setting_key='telegram_token'), 'telegram_token', ?, ?)", (token, now))
            
            # Upsert logic for chat_id
            cursor.execute("INSERT OR REPLACE INTO settings (id, setting_key, setting_value, updated_at) VALUES ((SELECT id FROM settings WHERE setting_key='telegram_chat_id'), 'telegram_chat_id', ?, ?)", (chat_id, now))
            
            conn.commit()
            self.telegram_token = token
            self.telegram_chat_id = chat_id
            return True
        except Exception as e:
            conn.rollback()
            logger.error(f"Ayarlar güncellenemedi: {e}")
            return False
        finally:
            conn.close()
