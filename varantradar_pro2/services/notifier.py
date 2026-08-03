import json
from utils.logger import logger

class NotificationSystem:
    def __init__(self):
        # In production, load from config or DB
        self.telegram_token = None
        self.chat_id = None
        self.email_settings = None

    def send_telegram_alert(self, message: str) -> bool:
        if not self.telegram_token or not self.chat_id:
            logger.debug(f"[MOCK TELEGRAM] Mesaj gönderilemedi (Token eksik): {message}")
            return False
            
        # Actual implementation would use requests.post to Telegram API
        logger.info(f"[TELEGRAM] Mesaj başarıyla iletildi: {message}")
        return True

    def send_desktop_notification(self, title: str, message: str):
        # Mock desktop notification
        logger.info(f"[MASAÜSTÜ BİLDİRİM] {title}: {message}")

    def trigger_smart_alert(self, symbol: str, score: float, action: str):
        """
        Triggers multi-channel alerts if confidence score exceeds a threshold.
        """
        if score >= 85 and action == "AL":
            alert_msg = f"🚨 GÜÇLÜ AL SİNYALİ 🚨\nHisse: {symbol}\nGüven Puanı: {score}/100"
            self.send_telegram_alert(alert_msg)
            self.send_desktop_notification("VarantRadar Pro Sinyali", alert_msg)
        elif score <= 20 and action == "SAT":
            alert_msg = f"📉 GÜÇLÜ SAT SİNYALİ 📉\nHisse: {symbol}\nGüven Puanı: {score}/100"
            self.send_telegram_alert(alert_msg)
            self.send_desktop_notification("VarantRadar Pro Sinyali", alert_msg)

notifier = NotificationSystem()
