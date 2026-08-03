import pandas as pd
from typing import Dict, Any
from .base_agent import BaseAgent

class VolumeAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="Volume Agent", role="Sadece hacim artışlarına, likiditeye ve VWAP konumuna bakar.")
        
    def analyze(self, df: pd.DataFrame, context: Dict[str, Any] = None) -> Dict[str, Any]:
        if df.empty or context is None:
            return {"Vote": 0, "Reason": "Veri yok.", "Confidence": 0}
            
        vol_data = context.get('vol', {})
        vwap_dist = vol_data.get('VWAP_Distance_Pct', 0)
        rel_vol = vol_data.get('Relative_Volume', 1.0)
        
        vote = 0
        reason = ""
        conf = 50
        
        if rel_vol > 1.5 and vwap_dist > 0:
            vote = 1
            reason = f"Hacim patlaması var (RV: {rel_vol:.1f}x) ve fiyat kurumsal ortalamanın (VWAP) üzerinde. Alıcılar çok güçlü."
            conf = 90
        elif rel_vol > 1.5 and vwap_dist < 0:
            vote = -1
            reason = f"Hacimli bir düşüş var. Fiyat VWAP'ın altında eziliyor. Ciddi bir likidite çıkışı yaşanıyor."
            conf = 85
        elif rel_vol < 0.7:
            vote = 0
            reason = "Hacim (Likidite) çok düşük. Şu anki fiyat hareketine güvenmiyorum, sahte olabilir."
            conf = 60
        else:
            if vwap_dist > 0:
                vote = 1
                reason = "Hacim normal seviyelerde ancak fiyat VWAP üzerinde destek bulmayı başarıyor."
                conf = 60
            else:
                vote = -1
                reason = "Fiyat VWAP altında kaldı, zayıf bir hacimle direnmeye çalışıyor."
                conf = 60
                
        return {"Vote": vote, "Reason": reason, "Confidence": conf}
