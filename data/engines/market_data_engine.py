import pandas as pd
from typing import Optional
from data.source_manager import DataSourceManager, ValidatedDataResult

class MarketDataEngine:
    """
    CFG-03.2 — MARKET DATA ENGINE
    
    Hisse, Varant, Endeks, ETF, Döviz, Emtia gibi temel fiyat/hacim (OHLCV) verilerinin çekilmesinden
    ve standart formatta sunulmasından sorumludur.
    """
    
    def __init__(self, source_manager: Optional[DataSourceManager] = None):
        self.source_manager = source_manager or DataSourceManager()
        
    def get_historical_prices(self, symbol: str, period: str = "6mo", interval: str = "1d") -> ValidatedDataResult:
        """Belirtilen sembol için geçmiş fiyat verilerini (OHLCV) döner."""
        return self.source_manager.fetch_validated(symbol, period, interval)
    
    def get_current_price(self, symbol: str) -> Optional[float]:
        """Sadece son fiyatı döner."""
        res = self.get_historical_prices(symbol, period="5d", interval="1d")
        if res.is_valid and not res.df.empty:
            return float(res.df['close'].iloc[-1])
        return None
        
    def get_atr(self, symbol: str, period: int = 14) -> Optional[float]:
        """Average True Range (ATR) hesaplar."""
        res = self.get_historical_prices(symbol, period="3mo", interval="1d")
        if res.is_valid and not res.df.empty and len(res.df) >= period:
            df = res.df
            high_low = df['high'] - df['low']
            atr = high_low.rolling(period).mean().iloc[-1]
            return float(atr)
        return None
