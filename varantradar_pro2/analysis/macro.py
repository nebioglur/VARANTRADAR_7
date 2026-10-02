import pandas as pd
import numpy as np
from typing import Dict, Any, Union
from core.interfaces import BaseEngine
from data.engines.macro_engine import MacroEngine as DataMacroEngine

class MacroEngine(BaseEngine):
    """
    CFG-04 Analysis Architecture (Macro Regime Engine)
    Ana endeks (Örn: XU100) verisi üzerinden Boğa (Bull), Ayı (Bear)
    veya Yatay (Sideways) piyasa rejimini belirler.
    BaseEngine standartlarına uygun (0-100) skor döner.
    """
    
    def analyze(self, symbol: str, data: Any = None) -> Dict[str, Union[float, str]]:
        result = {
            "Score": 50.0,
            "Status": "UNKNOWN",
            "Regime": "UNKNOWN",
            "Volatility": "UNKNOWN",
            "Verdict": "Yetersiz Veri"
        }
        
        try:
            data_engine = DataMacroEngine()
            regime = data_engine.get_market_regime()
            vix = data_engine.get_vix_level()
            
            score = 50.0
            status_text = "Piyasa yatay seyrediyor."
            
            if regime == "BULL":
                status_text = "Risk-On. Piyasa güçlü bir yükseliş trendinde."
                score = 80.0
                regime_tr = "BOĞA"
            elif regime == "BEAR":
                status_text = "Risk-Off. Piyasa düşüş trendinde, savunmada kal."
                score = 20.0
                regime_tr = "AYI"
            else:
                regime_tr = "YATAY"
                
            vol_status = "NORMAL"
            if vix and vix > 25.0:
                vol_status = "YÜKSEK VOLATİLİTE"
                status_text += " (VIX alarmı - Panik yüksek)"
                score -= 10.0
            elif vix and vix < 15.0:
                vol_status = "DÜŞÜK VOLATİLİTE"
                
            score = max(0.0, min(100.0, float(score)))
            result["Score"] = score
            result["Status"] = regime_tr
            result["Regime"] = regime_tr
            result["Volatility"] = vol_status
            result["Verdict"] = status_text
            
        except Exception as e:
            print(f"[MacroEngine] Hata: {e}")
            
        self.validate_output(result)
        return result
