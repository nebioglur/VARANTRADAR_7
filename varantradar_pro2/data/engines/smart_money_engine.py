from typing import Dict, Optional
from data.source_manager import DataSourceManager

class SmartMoneyEngine:
    """
    CFG-03.2 — SMART MONEY ENGINE
    
    Hacim analizi, blok işlemler, likidite, para akışı verilerini sağlar.
    """
    
    def __init__(self, source_manager: Optional[DataSourceManager] = None):
        self.source_manager = source_manager or DataSourceManager()
        
    def analyze_volume(self, symbol: str) -> Dict[str, float]:
        """Hacim anomalilerini ve akıllı para izlerini analiz eder."""
        res = self.source_manager.fetch_validated(symbol, period="1mo", interval="1d")
        if res.is_valid and not res.df.empty:
            df = res.df.copy()
            df.columns = [str(c).lower() for c in df.columns]
            
            if 'volume' not in df.columns:
                df['volume'] = 0.0
                
            avg_vol = df['volume'].mean()
            last_vol = df['volume'].iloc[-1]
            spike_ratio = last_vol / avg_vol if avg_vol > 0 else 1.0
            
            return {
                "avg_volume": avg_vol,
                "last_volume": last_vol,
                "spike_ratio": spike_ratio
            }
            
        return {
            "avg_volume": 0.0,
            "last_volume": 0.0,
            "spike_ratio": 1.0
        }
        
    def get_money_flow_index(self, symbol: str) -> Optional[float]:
        """MFI (Money Flow Index) hesaplar."""
        # TODO: MFI hesaplaması eklenecek
        return 65.0
