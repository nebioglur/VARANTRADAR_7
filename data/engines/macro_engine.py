from typing import Dict, Optional
import pandas as pd
from data.source_manager import DataSourceManager

class MacroEngine:
    """
    CFG-03.2 — MACRO DATA ENGINE
    
    Faiz oranları, Enflasyon, VIX (Korku Endeksi), Tahvil Faizleri gibi makro verileri izler.
    """
    
    def __init__(self, source_manager: Optional[DataSourceManager] = None):
        self.source_manager = source_manager or DataSourceManager()
        
    @staticmethod
    def _flatten_columns(df: pd.DataFrame) -> pd.DataFrame:
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df.columns = [str(c).lower() for c in df.columns]
        return df

    def get_market_regime(self) -> str:
        """Piyasa rejimini (Boğa/Ayı/Yatay) belirler."""
        res = self.source_manager.fetch_validated("^GSPC", period="6mo", interval="1d")
        if res.is_valid and not res.df.empty:
            df = self._flatten_columns(res.df.copy())
            current = df['close'].iloc[-1]
            ma200 = df['close'].rolling(200).mean().iloc[-1] if len(df) >= 200 else df['close'].mean()
            
            if current > ma200 * 1.05:
                return "BULL"
            elif current < ma200 * 0.95:
                return "BEAR"
            else:
                return "CHOPPY"
        return "UNKNOWN"
        
    def get_vix_level(self) -> Optional[float]:
        """VIX oynaklık endeksini döner."""
        res = self.source_manager.fetch_validated("^VIX", period="5d", interval="1d")
        if res.is_valid and not res.df.empty:
            df = self._flatten_columns(res.df.copy())
            return float(df['close'].iloc[-1])
        return None
