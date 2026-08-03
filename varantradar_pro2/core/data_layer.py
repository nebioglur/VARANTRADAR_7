import pandas as pd
from typing import Dict, Any, Optional
from engines.market_data_engine import MarketDataEngine

class UnifiedDataLayer:
    """
    FinOS Merkezi Veri Katmanı.
    Tüm veri talepleri (BIST, VIOP, Kripto) buradan geçer. 
    İleride farklı API'ler (Matriks, Binance vs.) eklense bile, sistemin geri kalanı (Kernel, Ajanlar) sadece bu sınıfla konuşur.
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(UnifiedDataLayer, cls).__new__(cls)
            cls._instance.md_engine = MarketDataEngine()
            cls._instance.cache = {} # Basit bir In-Memory Cache (Bellek İçi Önbellek)
        return cls._instance

    def fetch_market_data(self, symbol: str, asset_class: str = "EQUITY", period: str = "1y", interval: str = "1d") -> pd.DataFrame:
        """
        Varlığın sınıfına göre (BIST Hisse, Kripto vs.) uygun API'ye yönlendirir
        ve sonucu önbelleğe (Cache) alır.
        """
        cache_key = f"{symbol}_{period}_{interval}"
        
        # Eğer veri zaten çekildiyse ve bellekteyse direkt oradan ver (Performans artışı)
        if cache_key in self.cache:
            return self.cache[cache_key]
            
        # Şimdilik tüm asset sınıflarını (BIST) yfinance destekli MarketDataEngine'e yönlendiriyoruz
        # İleride "CRYPTO" gelirse binance_api'ye yönlendirilebilir.
        df = self.md_engine.fetch_data(symbol, period=period, interval=interval)
        
        if not df.empty:
            self.cache[cache_key] = df
            
        return df
        
    def clear_cache(self):
        """Önbelleği temizler (Sistem sağlığı için)"""
        self.cache = {}
