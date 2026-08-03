import pandas as pd
import numpy as np
from typing import Dict, Any

class AIDecisionEngine:
    """
    Teknik, Hacim ve Akıllı Para verilerini sentezleyerek
    Nihai Yön Kararını (Güçlü AL, SAT, Bekle) ve 
    AI Güven Skorunu (AI Confidence Score) hesaplar.
    """
    
    @staticmethod
    def calculate_decision(df: pd.DataFrame, tech_indicators: Dict[str, Any], smart_money_score: int, vwap_distance: float) -> Dict[str, Any]:
        """
        Gelen parametreler üzerinden Karar Ağacı simülasyonu çalıştırır.
        """
        if df.empty:
            return {"Decision": "VERİ YOK", "Confidence": 0}
            
        score = 50 # Nötr başlangıç noktası (0-100)
        
        # 1. Teknik İndikatör Katkısı
        rsi = tech_indicators.get('RSI', 50)
        macd_hist = tech_indicators.get('MACD_Hist', 0)
        
        if rsi < 30: 
            score += 15 # Aşırı satım, tepki gelebilir
        elif rsi > 70: 
            score -= 15 # Aşırı alım, düzeltme gelebilir
        elif rsi > 50:
            score += 5 # Yükseliş trendi
        else:
            score -= 5
            
        if macd_hist > 0:
            score += 10
        elif macd_hist < 0:
            score -= 10
            
        # 2. Smart Money Katkısı
        if smart_money_score >= 70:
            score += 20
        elif smart_money_score <= 30:
            score -= 20
            
        # 3. VWAP (Kurumsal Maliyet) Katkısı
        if vwap_distance > 5.0: # VWAP'tan çok uzaklaşmış (Şişmiş)
            score -= 10
        elif 0 < vwap_distance <= 5.0: # VWAP'ın hemen üstünde destek bulmuş
            score += 10
        elif -5.0 <= vwap_distance < 0: # VWAP direncini kırmaya çalışıyor
            score -= 5
        elif vwap_distance < -5.0: # VWAP'ın çok altında ezilmiş
            score -= 15
            
        # Skoru Sınırla
        final_score = min(100, max(0, score))
        
        # Karar Çıkarımı
        if final_score >= 85:
            decision = "GÜÇLÜ AL"
        elif final_score >= 65:
            decision = "AL"
        elif final_score >= 55:
            decision = "İZLEMEYE DEĞER (Pozitif Nötr)"
        elif final_score >= 45:
            decision = "BEKLE (Nötr)"
        elif final_score >= 35:
            decision = "DÜZELTME BEKLENEBİLİR (Negatif Nötr)"
        elif final_score >= 15:
            decision = "SAT"
        else:
            decision = "GÜÇLÜ SAT"
            
        # Güven Skoru (Confidence Level) - Sinyallerin birbirini teyit etme derecesi
        # Örneğin: Hem RSI çok düşük, hem Smart Money 80 ise uyum var, güven yüksektir.
        # Basitleştirilmiş Güven Hesaplaması: Uç noktalara yaklaştıkça güven artar.
        distance_from_neutral = abs(final_score - 50) 
        # Maksimum mesafe 50. Bunu 100'lük skalaya çevir.
        base_confidence = (distance_from_neutral / 50) * 100
        
        # Ek Güven Çarpanı: Yeterli veri/bar sayısı
        bar_penalty = 1.0 if len(df) >= 200 else (0.8 if len(df) >= 50 else 0.5)
        
        ai_confidence = min(99.0, max(10.0, base_confidence * bar_penalty))
        
        return {
            "Raw_Score": final_score,
            "Decision": decision,
            "Confidence": round(ai_confidence, 1),
            "Probability": f"%{round(ai_confidence, 1)} Olasılıkla {decision.split()[0]} Yönlü"
        }
