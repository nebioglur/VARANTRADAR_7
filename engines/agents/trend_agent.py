import pandas as pd
from typing import Dict, Any
from .base_agent import BaseAgent

class TrendAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="Trend Agent", role="Sadece fiyattaki trende, momentumlara ve hareketli ortalamalara bakar.")
        
    def analyze(self, df: pd.DataFrame, context: Dict[str, Any] = None) -> Dict[str, Any]:
        if df.empty or context is None:
            return {"Vote": 0, "Reason": "Veri yok.", "Confidence": 0}
            
        tech = context.get('tech', {})
        rsi = tech.get('RSI', pd.Series())
        macd = tech.get('MACD_Hist', pd.Series())
        
        rsi_val = rsi.iloc[-1] if not rsi.empty else 50
        macd_val = macd.iloc[-1] if not macd.empty else 0
        
        vote = 0
        reason = ""
        conf = 50
        
        if rsi_val > 50 and macd_val > 0:
            vote = 1
            reason = f"Momentum çok güçlü. RSI ({rsi_val:.1f}) 50'nin üzerinde ve MACD pozitif bölgede (Yükseliş Trendi)."
            conf = 85 if rsi_val > 60 else 70
        elif rsi_val < 50 and macd_val < 0:
            vote = -1
            reason = f"Trend aşağı yönlü. RSI ({rsi_val:.1f}) 50'nin altında ve MACD negatif."
            conf = 80 if rsi_val < 40 else 65
        else:
            vote = 0
            reason = "Trend şu an kararsız bir bölgede. Göstergeler yön konusunda fikir birliğine varamıyor."
            conf = 40
            
        return {"Vote": vote, "Reason": reason, "Confidence": conf}
