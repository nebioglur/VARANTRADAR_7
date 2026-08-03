from abc import ABC, abstractmethod
import pandas as pd
import time

class BaseDataProvider(ABC):
    """
    CFG-03.1 Enterprise Data Architecture
    Tüm veri sağlayıcıları (YFinance, Finnhub, Alpha Vantage vb.) bu standart arayüzü
    uygulamak zorundadır.
    
    Genişletilmiş Interface:
    - fetch_ohlcv: Fiyat verisi çekimi
    - get_provider_name: Sağlayıcı adı
    - health_check: Sağlık kontrolü (up/down)
    - get_latency: Son istek gecikmesi (ms)
    - get_priority: Failover sırasındaki öncelik (1=Primary)
    """
    
    def __init__(self):
        self._last_latency_ms = 0.0
        self._last_success_time = None
        self._error_count = 0
        self._success_count = 0
    
    @abstractmethod
    def fetch_ohlcv(self, symbol: str, period: str, interval: str) -> pd.DataFrame:
        """Hisse fiyat/hacim (OHLCV) verisini çeker."""
        pass
        
    @abstractmethod
    def get_provider_name(self) -> str:
        """Sağlayıcı adını döner."""
        pass
    
    @abstractmethod
    def get_priority(self) -> int:
        """Failover önceliği (1=Primary, 2=Secondary, 3=Backup)."""
        pass
    
    def health_check(self) -> dict:
        """Provider'ın sağlık durumunu döner."""
        total = self._success_count + self._error_count
        success_rate = (self._success_count / total * 100) if total > 0 else 0
        
        return {
            "provider": self.get_provider_name(),
            "priority": self.get_priority(),
            "status": "UP" if success_rate > 50 or total == 0 else "DEGRADED",
            "last_latency_ms": round(self._last_latency_ms, 1),
            "success_rate": round(success_rate, 1),
            "total_requests": total,
            "error_count": self._error_count
        }
    
    def get_latency(self) -> float:
        """Son istek gecikmesi (milisaniye)."""
        return self._last_latency_ms
    
    def _record_success(self, latency_ms: float):
        """Başarılı istek kaydı."""
        self._last_latency_ms = latency_ms
        self._last_success_time = time.time()
        self._success_count += 1
    
    def _record_error(self):
        """Başarısız istek kaydı."""
        self._error_count += 1
