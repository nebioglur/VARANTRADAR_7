import pandas as pd
import numpy as np
from typing import Dict, Any, Union
from core.interfaces import BaseEngine
from data.engines.smart_money_engine import SmartMoneyEngine as DataSmartMoneyEngine

class SmartMoneyEngine(BaseEngine):
    """
    CFG-04 Analysis Architecture (Smart Money)
    OHLCV verilerini kullanarak kurumsal likidite ve hacim izlerini arar.
    BaseEngine standartlarına uygun (0-100) skor döner.
    """
    
    def analyze(self, symbol: str, data: Any = None) -> Dict[str, Union[float, str]]:
        result = {
            "Score": 50.0,
            "Status": "UNKNOWN",
            "Verdict": "Veri yok veya yetersiz."
        }
        
        if data is None or not isinstance(data, pd.DataFrame) or data.empty or len(data) < 21:
            self.validate_output(result)
            return result
            
        df = data
        
        try:
            data_engine = DataSmartMoneyEngine()
            volume_metrics = data_engine.analyze_volume(symbol)
            mfi = data_engine.get_money_flow_index(symbol)
            
            smart_score = 50.0
            spike = volume_metrics.get("spike_ratio", 1.0)
            
            if spike > 3.0:
                smart_score += 15
                obv_trend = "UP"
            elif spike < 0.5:
                smart_score -= 10
                obv_trend = "DOWN"
            else:
                obv_trend = "FLAT"
                
            if mfi and mfi < 30: smart_score += 15 # Akümülasyon bölgesi
            elif mfi and mfi > 70: smart_score -= 20 # Dağıtım bölgesi
            
            smart_score = max(0.0, min(100.0, float(smart_score)))
            result["Score"] = smart_score
            
            if smart_score >= 70:
                result["Status"] = "AKÜMÜLASYON"
                result["Verdict"] = f"Büyük Para Topluyor (MFI: {mfi}, Hacim: {round(spike, 1)}x)"
            elif smart_score <= 35:
                result["Status"] = "DAĞITIM"
                result["Verdict"] = f"Büyük Para Çıkıyor (Satış Baskısı, MFI: {mfi})"
            else:
                result["Status"] = "NÖTR"
                result["Verdict"] = "Kurumsal tarafta net bir yön yok."
                
        except Exception as e:
            print(f"[SmartMoneyEngine] Hata: {e}")
            
        self.validate_output(result)
        return result
