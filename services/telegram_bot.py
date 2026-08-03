import requests
from config.settings import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from utils.logger import logger

class TelegramService:
    def __init__(self):
        self.token = TELEGRAM_BOT_TOKEN
        self.chat_id = TELEGRAM_CHAT_ID
        self.api_url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        
    def is_configured(self):
        return self.token != "BURAYA_TOKEN_YAZIN" and self.chat_id != "BURAYA_CHAT_ID_YAZIN"
        
    def send_message(self, text: str):
        if not self.is_configured():
            logger.warning("Telegram is not configured. Skipping message.")
            return False
            
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "HTML"
        }
        
        try:
            response = requests.post(self.api_url, json=payload, timeout=10)
            if response.status_code == 200:
                logger.info("Telegram message sent successfully.")
                return True
            else:
                logger.error(f"Failed to send Telegram message: {response.text}")
                return False
        except Exception as e:
            logger.error(f"Exception sending Telegram message: {str(e)}")
            return False

    def send_alert(self, signal_data: dict):
        """
        Formats and sends an AL/SAT alert.
        """
        symbol = signal_data.get('symbol', 'Bilinmiyor')
        action = signal_data.get('action', 'BEKLE')
        score = signal_data.get('score', 0)
        reasoning = signal_data.get('reasoning', '')
        
        action_icon = "🟢 GÜÇLÜ AL" if action == "AL" else "🔴 GÜÇLÜ SAT"
        
        msg = (
            f"🚨 <b>YENİ FIRSAT YAKALANDI!</b> 🚨\n\n"
            f"<b>Hisse:</b> {symbol}\n"
            f"<b>Sinyal:</b> {action_icon}\n"
            f"<b>Puan:</b> {score}/100\n\n"
            f"<b>Tespit Nedeni:</b>\n{reasoning}\n\n"
            f"<i>VarantRadar Pro Otomatik Tarama Sistemi</i>"
        )
        
        return self.send_message(msg)
