import time
import datetime
from services.screener import MarketScreener
from services.telegram_bot import TelegramService
from config.bist_symbols import BIST30_SYMBOLS
from utils.logger import logger

class AutomationBot:
    def __init__(self):
        self.screener = MarketScreener()
        self.telegram = TelegramService()
        self.notified_signals = {}  # Format: {'ASELS.IS': {'action': 'AL', 'time': timestamp}}
        self.cooldown_minutes = 60 * 4 # 4 hours cooldown per stock to avoid spam

    def start(self, interval_minutes=15):
        if not self.telegram.is_configured():
            logger.error("Telegram is not configured! Please update config/settings.py with your Token and Chat ID.")
            print("❌ Telegram Bot Token veya Chat ID eksik! Lütfen config/settings.py dosyasını güncelleyin.")
            return

        print(f"🚀 VarantRadar Otomasyon Botu Başlatıldı! (Tarama Aralığı: {interval_minutes} dakika)")
        self.telegram.send_message("✅ <b>VarantRadar Pro Botu Aktif!</b> Piyasa taraması başlatıldı.")

        while True:
            self.run_scan_cycle()
            
            # Wait for next cycle
            next_run = datetime.datetime.now() + datetime.timedelta(minutes=interval_minutes)
            print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Uykuya geçildi. Bir sonraki tarama: {next_run.strftime('%H:%M:%S')}")
            time.sleep(interval_minutes * 60)

    def run_scan_cycle(self):
        print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Piyasalar taranıyor...")
        
        # Sadece BIST30'u tara (hızlı ve kaliteli sinyaller için)
        results_df = self.screener.run_screener(BIST30_SYMBOLS)
        
        if results_df.empty:
            print("-> Kayda değer güçlü bir sinyal bulunamadı.")
            return

        for _, row in results_df.iterrows():
            symbol = row['symbol']
            action = row['action']
            score = row['score']
            
            # Check if we should notify
            if self.should_notify(symbol, action):
                print(f"-> YENİ SİNYAL: {symbol} - {action} (Puan: {score})")
                
                # Send Telegram Alert
                success = self.telegram.send_alert(row.to_dict())
                
                if success:
                    # Update cache
                    self.notified_signals[symbol] = {
                        'action': action,
                        'time': time.time()
                    }

    def should_notify(self, symbol, current_action):
        """
        Prevents spamming the same signal over and over.
        Only notifies if it's a NEW signal or if the cooldown has expired.
        """
        if symbol not in self.notified_signals:
            return True
            
        last_notification = self.notified_signals[symbol]
        
        # If the action has changed (e.g. from AL to SAT), notify immediately
        if last_notification['action'] != current_action:
            return True
            
        # If action is the same, check cooldown
        time_elapsed = time.time() - last_notification['time']
        if time_elapsed > (self.cooldown_minutes * 60):
            return True
            
        return False

if __name__ == "__main__":
    bot = AutomationBot()
    # Piyasayı 15 dakikada bir tarar
    bot.start(interval_minutes=15)
