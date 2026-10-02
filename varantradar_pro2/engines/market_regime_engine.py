import pandas as pd
import numpy as np
from typing import Dict, Any

class MarketRegimeEngine:
    """
    Piyasanın genel durumunu (Makro/Rejim) analiz eder.
    Ana endeks verisi üzerinden Boğa (Bull), Ayı (Bear) veya Yatay (Sideways) piyasa rejimini belirler.
    """
    
    @staticmethod
    def analyze_regime(df_index: pd.DataFrame) -> Dict[str, Any]:
        """
        Girdi: Ana endeks (Örn: XU100.IS) dataframe'i.
        Çıktı: Piyasa rejimi ve volatilite durumu.
        """
        if df_index.empty or len(df_index) < 50:
            return {"Regime": "UNKNOWN", "Status": "Yetersiz Veri", "Volatility": "UNKNOWN"}
            
        close = df_index['Close']
        
        # Basit Hareketli Ortalamalar (Trend tespiti için)
        sma20 = close.rolling(window=20).mean()
        sma50 = close.rolling(window=50).mean()
        
        current_close = close.iloc[-1]
        current_sma20 = sma20.iloc[-1]
        current_sma50 = sma50.iloc[-1]
        
        # Volatilite (ATR)
        high_low = df_index['High'] - df_index['Low']
        high_close = np.abs(df_index['High'] - close.shift())
        low_close = np.abs(df_index['Low'] - close.shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = np.max(ranges, axis=1)
        atr14 = true_range.rolling(14).mean()
        
        current_atr = atr14.iloc[-1]
        atr_pct = (current_atr / current_close) * 100
        
        # Rejim Kararı
        regime = "YATAY (SIDEWAYS)"
        status_text = "Piyasa belirgin bir yöne sahip değil."
        
        if current_close > current_sma20 and current_sma20 > current_sma50:
            regime = "BOĞA (BULL)"
            status_text = "Risk-On. Piyasa güçlü bir yükseliş trendinde."
        elif current_close < current_sma20 and current_sma20 < current_sma50:
            regime = "AYI (BEAR)"
            status_text = "Risk-Off. Piyasa düşüş trendinde, savunmada kal."
            
        # Volatilite Kararı
        vol_status = "NORMAL"
        if atr_pct > 3.0: # Endeks için günlük %3 üstü dalgalanma çok yüksektir
            vol_status = "YÜKSEK VOLATİLİTE"
            status_text += " Dikkat: Piyasada panik/dalgalanma yüksek."
        elif atr_pct < 1.0:
            vol_status = "DÜŞÜK VOLATİLİTE"
            
        return {
            "Regime": regime,
            "Volatility": vol_status,
            "Status": status_text,
            "Metrics": {
                "SMA20": round(current_sma20, 2),
                "SMA50": round(current_sma50, 2),
                "ATR_Pct": round(atr_pct, 2)
            }
        }
