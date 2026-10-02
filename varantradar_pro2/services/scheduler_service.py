import time
import threading
from datetime import datetime
from services.radar_engine import RadarEngine
from services.notification_manager import NotificationManager
from config.bist_symbols import BIST30_SYMBOLS
from utils.logger import logger

class SchedulerService:
    """
    VarantRadar Pro V7 - Otomasyon Motoru
    Arka planda çalışarak belirlenen periyotlarda piyasayı tarar ve sinyal üretirse Telegram'a atar.
    """
    def __init__(self, interval_minutes: int = 60):
        self.interval_minutes = interval_minutes
        self.is_running = False
        self.thread = None
        self.radar = RadarEngine()
        self.notifier = NotificationManager()

    def _job(self):
        logger.info(f"V7 Otomasyon Botu Başladı. Tarama Aralığı: {self.interval_minutes} dakika.")
        while self.is_running:
            try:
                # Sadece hafta içi ve çalışma saatlerinde tarama yapsın (Basit kontrol)
                now = datetime.now()
                if now.weekday() < 5 and 9 <= now.hour <= 18:
                    logger.info("Otomatik Tarama Tetiklendi...")
                    
                    # BIST30'u hızlıca tara
                    results_df = self.radar.run_radar(BIST30_SYMBOLS, max_workers=3)
                    
                    if not results_df.empty:
                        # En iyi 1 fırsatı al (Spam yapmamak için sadece puanı 80 üstü olan S veya A sınıfı)
                        top_opp = results_df.iloc[0]
                        if top_opp['Puan'] >= 80:
                            self.notifier.send_radar_alert(
                                symbol=top_opp['Hisse'],
                                score=top_opp['Puan'],
                                level=top_opp['Seviye'],
                                reason="Otomatik Tarama Motoru bu hissede güçlü bir kırılım yakaladı."
                            )
                else:
                    logger.info("Piyasa kapalı, tarama atlandı.")
                    
            except Exception as e:
                logger.error(f"Otomasyon Motoru Hatası: {e}")
                
            # Bekleme süresi
            for _ in range(self.interval_minutes * 60):
                if not self.is_running:
                    break
                time.sleep(1)
                
        logger.info("V7 Otomasyon Botu Durduruldu.")

    def start(self):
        if not self.is_running:
            self.is_running = True
            self.thread = threading.Thread(target=self._job, daemon=True)
            self.thread.start()
            return True
        return False

    def stop(self):
        if self.is_running:
            self.is_running = False
            if self.thread:
                self.thread.join(timeout=2)
            return True
        return False

    def status(self) -> str:
        return "Çalışıyor 🟢" if self.is_running else "Durdu 🔴"
