import yfinance as yf
import pandas as pd
import time
from data.providers.base_provider import BaseDataProvider

class YFinanceProvider(BaseDataProvider):
    """
    CFG-03.1 — PRIMARY DATA PROVIDER
    Yahoo Finance üzerinden piyasa verisi çeken API sınıfı.
    Priority: 1 (Primary)
    """
    
    def get_provider_name(self) -> str:
        return "YFinance API"
    
    def get_priority(self) -> int:
        return 1  # Primary
        
    def fetch_ohlcv(self, symbol: str, period: str = "1mo", interval: str = "1d") -> pd.DataFrame:
        """Belirtilen varlık için ham (raw) veriyi çeker (Retry mekanizmalı)."""
        retries = 3
        delay = 1.5
        
        for attempt in range(retries):
            try:
                start_time = time.time()
                ticker = yf.Ticker(symbol)
                df = ticker.history(period=period, interval=interval, repair=True)
                latency = (time.time() - start_time) * 1000  # ms
                
                if df is not None and not df.empty:
                    self._record_success(latency)
                    return df
                else:
                    if attempt < retries - 1:
                        time.sleep(delay)
                        continue
                    else:
                        self._record_error()
                        return pd.DataFrame()
                        
            except Exception as e:
                if attempt < retries - 1:
                    time.sleep(delay)
                    continue
                else:
                    self._record_error()
                    return pd.DataFrame()
                    
        self._record_error()
        return pd.DataFrame()
