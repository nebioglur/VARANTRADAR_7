import pandas as pd
from typing import Dict, Any

class BaseAgent:
    """
    Tüm uzman AI Ajanlarının türetileceği temel sınıf.
    Her ajan piyasaya kendi penceresinden bakar ve bir 'Oy (Vote)' ile 'Argüman (Reason)' sunar.
    """
    
    def __init__(self, name: str, role: str):
        self.name = name
        self.role = role
        
    def analyze(self, df: pd.DataFrame, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Girdi: Fiyat DataFrame'i ve diğer ön hesaplamalar (context).
        Çıktı: {"Vote": 1 (AL), 0 (BEKLE), -1 (SAT), "Reason": "Neden böyle düşündüğü", "Confidence": 0-100}
        """
        raise NotImplementedError("Her ajan kendi analyze metodunu yazmalıdır.")
