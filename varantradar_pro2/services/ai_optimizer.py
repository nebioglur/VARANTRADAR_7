import json
import os
from datetime import datetime
from utils.logger import logger

class AIOptimizer:
    """
    VarantRadar Pro V6 - AI Strateji Optimizasyonu ve Öğrenme
    Hatalardan ders alır ve strateji parametrelerini optimize eder.
    """
    def __init__(self):
        self.memory_file = "ai_memory.json"
        self._load_memory()

    def _load_memory(self):
        if os.path.exists(self.memory_file):
            try:
                with open(self.memory_file, 'r', encoding='utf-8') as f:
                    self.memory = json.load(f)
            except Exception as e:
                logger.error(f"AI Memory yüklenemedi: {e}")
                self.memory = {"failed_rules": [], "successful_rules": []}
        else:
            self.memory = {"failed_rules": [], "successful_rules": []}

    def _save_memory(self):
        try:
            with open(self.memory_file, 'w', encoding='utf-8') as f:
                json.dump(self.memory, f, indent=4)
        except Exception as e:
            logger.error(f"AI Memory kaydedilemedi: {e}")

    def optimize_parameters(self, strategy_type: str, current_win_rate: float) -> dict:
        """
        Modül 7: Eğer stratejinin Win Rate'i düşükse parametreleri optimize eder.
        """
        if strategy_type == "MACD_RSI_CROSS":
            if current_win_rate < 40:
                return {
                    "action": "UPDATE",
                    "new_params": {"rsi_oversold": 25, "rsi_overbought": 75},
                    "reason": "Win Rate %40'ın altında. RSI eşikleri daraltılarak daha az ama daha güvenli işlem (False-positive azaltımı) hedeflendi."
                }
            elif current_win_rate > 70:
                return {
                    "action": "KEEP",
                    "new_params": {},
                    "reason": "Mevcut parametreler harika çalışıyor."
                }
        
        return {"action": "KEEP", "new_params": {}, "reason": "Optimizasyona gerek duyulmadı."}

    def learn_from_trade(self, trade_info: dict):
        """
        Modül 10: AI Öğrenme Sistemi.
        Geçmiş işlemleri analiz edip belleğine kaydeder.
        """
        pnl = trade_info.get("pnl_pct", 0)
        duration = trade_info.get("duration", 0)
        
        # Öğrenme Kuralları
        if pnl < -10 and duration < 2:
            rule = f"Hızlı Çöküş Öğrenildi: Fiyat kırılımından hemen sonra çok yüksek hacimli satış yiyen hisselerde (Sahte Kırılım / Bull Trap) stop mesafesi %1.5'a çekilmeli."
            if rule not in self.memory['failed_rules']:
                self.memory['failed_rules'].append(rule)
                self._save_memory()
                
        elif pnl > 15 and duration > 5:
            rule = f"Trend Takibi Başarısı: 5 günden uzun süren ve %15 üzeri kazandıran işlemlerde Trailing Stop kullanılması kârı maksimize ediyor."
            if rule not in self.memory['successful_rules']:
                self.memory['successful_rules'].append(rule)
                self._save_memory()

    def get_ai_insights(self) -> list:
        """Kullanıcıya öğretileri sunar."""
        insights = []
        insights.extend([f"🔴 Kaçınılan Hata: {r}" for r in self.memory['failed_rules']])
        insights.extend([f"🟢 Başarılı Taktik: {r}" for r in self.memory['successful_rules']])
        
        if not insights:
            insights.append("Sistem henüz yeterli sayıda işlem yapmadığı için yeni bir kural öğrenmedi.")
            
        return insights
