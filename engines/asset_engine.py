from abc import ABC, abstractmethod
from typing import Dict, Any
import pandas as pd

class AssetEngine(ABC):
    """
    Base engine for all assets (Stock, Warrant, ETF, VIOP).
    CFG-03 Asset-first architecture.
    """
    
    @abstractmethod
    def analyze(self, symbol: str, data: pd.DataFrame, data_4h: pd.DataFrame = None) -> Dict[str, Any]:
        """
        Her varlık türü kendi analiz algoritmasını (fair value, greeks vb.) uygulayacaktır.
        """
        pass

class StockEngine(AssetEngine):
    """
    Hisse senetlerine özel hesaplama motoru.
    (Fair Value, Support, Resistance vb.)
    """
    def analyze(self, symbol: str, data: pd.DataFrame, data_4h: pd.DataFrame = None) -> Dict[str, Any]:
        if data.empty:
            return {}
            
        current_price = data['close'].iloc[-1]
        
        # Basit Fair Value & Destek/Direnç Proxy (Demo)
        resistance = data['high'].tail(14).max()
        support = data['low'].tail(14).min()
        
        return {
            "Symbol": symbol,
            "Type": "STOCK",
            "Price": round(current_price, 2),
            "Resistance": round(resistance, 2),
            "Support": round(support, 2)
        }

class WarrantEngine(AssetEngine):
    """
    Varantlara özel hesaplama motoru.
    (Delta, Theta, Effective Leverage vb.)
    """
    def analyze(self, symbol: str, data: pd.DataFrame, data_4h: pd.DataFrame = None) -> Dict[str, Any]:
        if data.empty:
            return {}
            
        current_price = data['close'].iloc[-1]
        
        # Varant Grekleri ve Metrikleri (Matematiksel Proxy - BIST'te canlı kapalı)
        return {
            "Symbol": symbol,
            "Type": "WARRANT",
            "Price": round(current_price, 2),
            "Greeks": {
                "Delta": "Canlı Veri Yok",
                "Theta": "Zaman Değeri",
                "Effective_Leverage": "API Gerekli"
            }
        }
