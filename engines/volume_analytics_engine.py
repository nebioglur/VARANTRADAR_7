import pandas as pd
import numpy as np
from typing import Dict, Any

class VolumeAnalyticsEngine:
    """
    Hacim profili, Göreceli Hacim (RV) ve Hacim Patlamalarını analiz eden motor.
    """
    
    @staticmethod
    def calculate_vwap(df: pd.DataFrame) -> pd.Series:
        """
        Gelen DataFrame (Örn: günlük veriler) üzerinden Kümülatif VWAP hesaplar.
        Normalde VWAP gün içi (Intraday) tick verisiyle hesaplanır, 
        ancak burada Anchored / Cumulative Daily VWAP simülasyonu yapıyoruz.
        """
        if df.empty or 'volume' not in df.columns:
            return pd.Series(dtype=float)
            
        typical_price = (df['high'] + df['low'] + df['close']) / 3
        volume = df['volume']
        
        cumulative_vp = (typical_price * volume).cumsum()
        cumulative_volume = volume.cumsum()
        
        vwap = cumulative_vp / cumulative_volume
        return pd.Series(vwap, index=df.index)

    @staticmethod
    def calculate_relative_volume(df: pd.DataFrame, period: int = 14) -> pd.Series:
        """
        Göreceli Hacim (Relative Volume - RV).
        Mevcut hacmin, geçmiş 'period' günlük ortalama hacme oranıdır.
        RV > 2.0 ise olağandışı hacim kabul edilir.
        """
        if df.empty or 'volume' not in df.columns:
            return pd.Series(dtype=float)
            
        avg_volume = df['volume'].rolling(window=period).mean().shift(1)
        # 0'a bölmeyi engelle
        avg_volume = avg_volume.replace(0, np.nan)
        
        rv = df['volume'] / avg_volume
        return pd.Series(rv, index=df.index)
        
    @staticmethod
    def analyze_volume(df: pd.DataFrame) -> Dict[str, Any]:
        """Genel hacim analizi ve uyarıları oluşturur."""
        if df.empty or len(df) < 15:
            return {"error": "Yeterli veri yok."}
            
        rv = VolumeAnalyticsEngine.calculate_relative_volume(df)
        vwap = VolumeAnalyticsEngine.calculate_vwap(df)
        
        latest_rv = rv.iloc[-1]
        latest_vwap = vwap.iloc[-1]
        current_price = df['close'].iloc[-1]
        
        # VWAP Durumu
        vwap_status = "BULLISH (VWAP Üzerinde)" if current_price > latest_vwap else "BEARISH (VWAP Altında)"
        vwap_distance_pct = ((current_price / latest_vwap) - 1) * 100
        
        # Hacim Uyarıları
        volume_status = "NORMAL"
        if latest_rv > 2.5:
            volume_status = "OLAĞANDIŞI YÜKSEK (Patlama)"
        elif latest_rv > 1.5:
            volume_status = "YÜKSEK"
        elif latest_rv < 0.5:
            volume_status = "ÇOK DÜŞÜK (Kuruma)"
            
        return {
            "Relative_Volume": round(latest_rv, 2),
            "Volume_Status": volume_status,
            "VWAP_Price": round(latest_vwap, 2),
            "VWAP_Status": vwap_status,
            "VWAP_Distance_Pct": round(vwap_distance_pct, 2)
        }
