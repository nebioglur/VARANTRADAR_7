from typing import Dict, Any, Union
from core.interfaces import BaseEngine
import math

class OptionsEngine(BaseEngine):
    """
    CFG-14 Varant & Opsiyon Analizi
    Hissenin spot (dayanak varlık) volatilitesine bakarak Kaldıraç, 
    Zımni Volatilite (IV Approximation) ve Theta Decay (Zaman Kaybı) riskini hesaplar.
    """
    
    def analyze(self, symbol: str, data: Any = None) -> Dict[str, Union[float, str]]:
        result = {
            "Score": 50.0,
            "Status": "UNKNOWN",
            "Implied_Volatility": "N/A",
            "Theta_Risk": "N/A",
            "Leverage_Suitability": "N/A"
        }
        
        if data is None or len(data) < 20:
            self.validate_output(result)
            return result
            
        try:
            df = data
            
            # Basit Tarihsel Volatilite Hesaplaması (Son 20 gün)
            df['Log_Ret'] = df['close'] / df['close'].shift(1)
            # Log getirisini bul (yaklaşık olarak return - 1 diyebiliriz ya da log() alabiliriz)
            import numpy as np
            log_returns = np.log(df['Log_Ret'].dropna())
            
            daily_volatility = log_returns.std()
            annualized_volatility = daily_volatility * math.sqrt(252) # 252 işlem günü
            
            iv_approx = annualized_volatility * 100 # % cinsinden
            
            # Varant için Yüksek Volatilite = Hızlı Fiyat Hareketi = İYİ (Fakat çok yüksekse prim pahalıdır)
            # Düşük Volatilite = Yatay Seyir = KÖTÜ (Theta decay parayı eritir)
            
            score = 50.0
            theta_risk = "ORTA"
            suitability = "UYGUN DEĞİL"
            
            if iv_approx < 15.0:
                score -= 20
                theta_risk = "YÜKSEK (Yatay Seyir Zaman Değerini Eritir)"
                suitability = "KALDIRAÇ İÇİN ZAYIF"
            elif 15.0 <= iv_approx <= 35.0:
                score += 20
                theta_risk = "DÜŞÜK (Trend Başlangıcı Olabilir)"
                suitability = "VARANT ALIMI İÇİN İDEAL"
            elif iv_approx > 35.0:
                score -= 10 # Primler çok şişmiş olabilir (IV Crush riski)
                theta_risk = "ORTA (IV Crush Riski Yüksek)"
                suitability = "YALNIZCA GÜN İÇİ SCALP UYGUN"
                
            score = max(0.0, min(100.0, score))
            
            result["Implied_Volatility"] = f"%{round(iv_approx, 1)}"
            result["Theta_Risk"] = theta_risk
            result["Leverage_Suitability"] = suitability
            result["Score"] = score
            
            if score >= 65:
                result["Status"] = "UYGUN"
            elif score <= 35:
                result["Status"] = "RİSKLİ"
            else:
                result["Status"] = "NÖTR"
                
        except Exception as e:
            print(f"[OptionsEngine] Hata: {e}")
            
        self.validate_output(result)
        return result
