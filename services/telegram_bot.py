from services.notification_manager import NotificationManager

class TelegramService:
    """
    VarantRadar Pro - Telegram Köprüsü
    NotificationManager ile tam entegre çalışır.
    """
    def __init__(self):
        self.notif = NotificationManager()
        
    def is_configured(self):
        return bool(self.notif.telegram_token and self.notif.telegram_chat_id and "BURAYA_" not in str(self.notif.telegram_token))
        
    def send_message(self, text: str):
        return self.notif.send_telegram_message(text)

    def send_alert(self, signal_data: dict):
        """
        Formats and sends an AL/SAT alert with full price details.
        """
        symbol = signal_data.get('symbol', 'Bilinmiyor').replace('.IS', '').upper()
        action = signal_data.get('action', 'BEKLE')
        score = signal_data.get('score', 0)
        price = signal_data.get('price') or signal_data.get('close')
        chg = signal_data.get('change_pct') or signal_data.get('daily_change_pct')
        reasoning = signal_data.get('reasoning', '')
        
        action_icon = "🟢 GÜÇLÜ AL" if action == "AL" else ("🔴 GÜÇLÜ SAT" if action == "SAT" else "🟡 İZLE")
        price_str = f"₺{float(price):.2f}" if price is not None else "-"
        chg_str = f" (%+{float(chg):.2f})" if chg and float(chg) > 0 else (f" (%{float(chg):.2f})" if chg else "")
        
        msg = (
            f"🚨 <b>YENİ FIRSAT YAKALANDI!</b> 🚨\n\n"
            f"📌 <b>Hisse:</b> #{symbol}\n"
            f"💰 <b>Anlık Fiyat:</b> {price_str}{chg_str}\n"
            f"🎯 <b>Sinyal:</b> {action_icon}\n"
            f"⭐ <b>AI Skoru:</b> {score}/100\n\n"
            f"💡 <b>Tespit Nedeni:</b>\n{reasoning}\n\n"
            f"🤖 <i>VarantRadar Pro Otomatik Tarama Sistemi</i>"
        )
        
        return self.send_message(msg)
