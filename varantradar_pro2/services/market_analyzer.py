import pandas as pd
import numpy as np

class MarketAnalyzer:
    """
    VarantRadar Pro V8 - Akıllı Piyasa Analizi
    BIST'in genel yönünü, hacmini ve sektörlerin gücünü hesaplar.
    """
    def __init__(self):
        pass
        
    def analyze_market_breadth(self, bist_data_df: pd.DataFrame) -> dict:
        """Modül 2: Tüm piyasadaki para girişi, hacim ve trend analizi."""
        if bist_data_df.empty:
            return {"trend": "Nötr", "volume_status": "Düşük", "strong_sectors": ""}
            
        # Basit bir simülasyon (Gerçekte tüm hisselerin kapanışları incelenir)
        # Örnek: Kapanışı dünkü kapanıştan yüksek olan hisse oranı
        
        up_count = len(bist_data_df[bist_data_df['Puan'] > 50])
        total_count = len(bist_data_df)
        breadth_ratio = up_count / total_count if total_count > 0 else 0.5
        
        if breadth_ratio > 0.6:
            trend = "Yükseliş (Boğa)"
            money_flow = "Pozitif Para Girişi"
        elif breadth_ratio < 0.4:
            trend = "Düşüş (Ayı)"
            money_flow = "Para Çıkışı"
        else:
            trend = "Yatay"
            money_flow = "Dengeli"
            
        return {
            "trend": trend,
            "breadth_ratio": round(breadth_ratio * 100, 1),
            "money_flow": money_flow,
            "volume_status": "Ortalama Üzeri" if breadth_ratio > 0.5 else "Zayıf",
            "strong_sectors": "Bankacılık, Holding" # Statik örnek, gerçekte API'den çekilir
        }
        
    def predict_target_duration(self, current_price: float, target_price: float, atr: float) -> dict:
        """Modül 6: Hedefe ulaşma süresini istatistiksel tahmin eder."""
        if atr <= 0:
            return {"days": 0, "confidence": 0}
            
        distance = abs(target_price - current_price)
        avg_days = distance / atr
        
        # Güven aralığı (Volatilite yüksekse güven düşer)
        confidence = max(10, min(90, 100 - (avg_days * 5)))
        
        return {
            "predicted_days": round(avg_days, 1),
            "confidence_pct": round(confidence, 1),
            "scenario": f"Mevcut volatilite ile {round(avg_days, 1)} gün içinde hedefe ulaşma ihtimali %{round(confidence, 1)}."
        }
