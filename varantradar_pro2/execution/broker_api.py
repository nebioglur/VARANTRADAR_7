from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseBrokerAPI(ABC):
    """
    CFG-11 Autonomous Trading (Broker Interface)
    Sistemin kendi kendine al-sat yapabilmesi için aracı kurumlarla (Midas, Binance, Info Yatırım vb.)
    konuşmasını sağlayan ortak arayüz.
    """
    
    @abstractmethod
    def connect(self) -> bool:
        """Broker sunucusuna bağlanıp API key doğrulamasını yapar."""
        pass
        
    @abstractmethod
    def send_market_order(self, symbol: str, side: str, quantity: int) -> Dict[str, Any]:
        """Piyasa fiyatından (Market Order) anında alım/satım yapar."""
        pass
        
    @abstractmethod
    def send_limit_order(self, symbol: str, side: str, quantity: int, price: float) -> Dict[str, Any]:
        """Belirlenen bir fiyattan (Limit Order) alım/satım emri girer."""
        pass
        
    @abstractmethod
    def send_oco_order(self, symbol: str, quantity: int, stop_price: float, target_price: float) -> Dict[str, Any]:
        """
        One-Cancels-the-Other (OCO) emri girer.
        Aynı anda hem Stop-Loss hem de Take-Profit emrini borsaya iletir. Biri gerçekleşirse diğeri iptal olur.
        """
        pass
