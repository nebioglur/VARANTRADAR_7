import pandas as pd
from typing import Dict, Any
from .base_agent import BaseAgent

class SmartMoneyAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="Smart Money Agent", role="Sadece fonların (büyük paranın) ne yaptığına ve Wyckoff döngülerine odaklanır.")
        
    def analyze(self, df: pd.DataFrame, context: Dict[str, Any] = None) -> Dict[str, Any]:
        if df.empty or context is None:
            return {"Vote": 0, "Reason": "Veri yok.", "Confidence": 0}
            
        sm_data = context.get('sm', {})
        sm_score = sm_data.get('Smart_Money_Score', 50)
        
        wyckoff = context.get('wyckoff', "UNKNOWN")
        
        vote = 0
        reason = ""
        conf = 50
        
        if sm_score > 65 and "ACCUMULATION" in wyckoff:
            vote = 1
            reason = f"Çok net bir Kurumsal Toplama (Accumulation) evresi var. Smart Money Skoru yüksek ({sm_score}). Büyük fonlar maliyetleniyor."
            conf = 95
        elif sm_score > 60:
            vote = 1
            reason = f"Kurumsal para girişi devam ediyor (Skor: {sm_score}). Fiyat hareketini destekliyor."
            conf = 80
        elif sm_score < 35 and "DISTRIBUTION" in wyckoff:
            vote = -1
            reason = f"Kurumsallar mal yıkıyor (Distribution evresi). Smart Money Skoru çok düşük ({sm_score}). Büyük kaçış var."
            conf = 95
        elif sm_score < 40:
            vote = -1
            reason = f"Büyük kurumsal oyunculardan belirgin bir para çıkışı izliyorum (Skor: {sm_score})."
            conf = 80
        else:
            vote = 0
            reason = f"Kurumsal tarafta net bir yön tayini yok (Skor: {sm_score}). Büyük paranın izi silik."
            conf = 50
            
        return {"Vote": vote, "Reason": reason, "Confidence": conf}
