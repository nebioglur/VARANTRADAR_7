import pandas as pd
from typing import Dict, Any
from .base_agent import BaseAgent

class RiskAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="Risk Agent (Şeytanın Avukatı)", role="Karamsardır. Sadece aşağı yönlü risklere, aşırılıklara ve olası tehlikelere odaklanır.")
        
    def analyze(self, df: pd.DataFrame, context: Dict[str, Any] = None) -> Dict[str, Any]:
        if df.empty or context is None:
            return {"Vote": 0, "Reason": "Veri yok.", "Confidence": 0}
            
        mani_risk = context.get('mani_risk', 0)
        tech = context.get('tech', {})
        rsi = tech.get('RSI', pd.Series())
        rsi_val = rsi.iloc[-1] if not rsi.empty else 50
        
        vote = 0
        reason = ""
        conf = 50
        
        # Risk ajanı asla "AL" (1) demez. Sadece 0 (Tarafsız) veya -1 (İtiraz / SAT) verir.
        
        if mani_risk > 60:
            vote = -1
            reason = f"Kritik İtiraz! Manipülasyon risk skoru çok yüksek ({mani_risk}/100). Fiyatlamada sahtelik olabilir."
            conf = 95
        elif rsi_val > 75:
            vote = -1
            reason = f"Güçlü İtiraz! RSI çok şişmiş ({rsi_val:.1f}). Düzeltme riski masada, alım için çok tehlikeli bir bölge."
            conf = 85
        elif rsi_val < 30:
            # RSI çok düşükse risk ajanı "sat" demez, tarafsız kalır (zaten düşmüş)
            vote = 0
            reason = f"Hisse aşırı satım bölgesinde (RSI: {rsi_val:.1f}). Zaten yeterince düşmüş, satmak için çok geç olabilir."
            conf = 70
        else:
            vote = 0
            reason = "Piyasada olağanüstü bir risk veya manipülasyon izi görmüyorum. Kararı diğer ajanlara bırakıyorum."
            conf = 40
            
        return {"Vote": vote, "Reason": reason, "Confidence": conf}
