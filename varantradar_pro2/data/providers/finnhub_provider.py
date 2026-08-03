import pandas as pd
import requests
import time
from typing import Optional
from data.providers.base_provider import BaseDataProvider
from data.security import Vault

class FinnhubProvider(BaseDataProvider):
    """
    CFG-03.1 — SECONDARY DATA PROVIDER
    Finnhub.io üzerinden piyasa verisi çeken API sınıfı.
    Priority: 2 (Secondary / Failover)
    
    Not: Finnhub ücretsiz planda sınırlı veri sunar.
    Gerçek kullanım için API key gerekir (FINNHUB_API_KEY env variable).
    Şu an yfinance'in alternatif kaynağı olarak çalışır.
    """
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://finnhub.io/api/v1"
        self.api_key = Vault.get_key("FINNHUB")
    
    def get_provider_name(self) -> str:
        return "Finnhub API"
    
    def get_priority(self) -> int:
        return 2  # Secondary
    
    def fetch_ohlcv(self, symbol: str, period: str = "1mo", interval: str = "1d") -> pd.DataFrame:
        """
        Finnhub'dan fiyat verisi çeker.
        API key yoksa veya hata oluşursa boş DataFrame döner (Failover zincirinde bir sonraki kaynağa geçilir).
        """
        if not self.api_key:
            self._record_error()
            return pd.DataFrame()
        
        try:
            import requests
            start_time = time.time()
            
            # Period -> Unix timestamp çevirimi
            period_days = {"1mo": 30, "3mo": 90, "6mo": 180, "1y": 365}.get(period, 30)
            end_ts = int(time.time())
            start_ts = end_ts - (period_days * 86400)
            
            # Finnhub OHLCV (Candle) endpoint
            # .IS suffix'i kaldır (Finnhub farklı sembol formatı kullanır)
            clean_symbol = symbol.replace(".IS", "")
            
            url = f"https://finnhub.io/api/v1/stock/candle?symbol={clean_symbol}&resolution=D&from={start_ts}&to={end_ts}&token={self.api_key}"
            response = requests.get(url, timeout=10)
            latency = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                data = response.json()
                if data.get("s") == "ok" and "c" in data:
                    df = pd.DataFrame({
                        "Open": data["o"],
                        "High": data["h"],
                        "Low": data["l"],
                        "Close": data["c"],
                        "Volume": data["v"]
                    })
                    self._record_success(latency)
                    return df
            
            self._record_error()
            return pd.DataFrame()
            
        except Exception as e:
            self._record_error()
            return pd.DataFrame()
