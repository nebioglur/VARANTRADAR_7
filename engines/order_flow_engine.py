import pandas as pd
import numpy as np
from typing import Dict, Any, List

class OrderFlowEngine:
    """
    Tick (Derinlik) verisi olmadığında OHLCV (Mum Çubukları) üzerinden
    Kurumsal Tuzakları (Fake Breakout, Liquidity Sweep) ve 
    Alıcı/Satıcı Emir Baskısını (Synthetic Order Imbalance) tahmin eder.
    """
    
    @staticmethod
    def analyze_synthetic_imbalance(df: pd.DataFrame, window: int = 5) -> pd.Series:
        """
        Buying Pressure vs Selling Pressure.
        Eğer kapanış mumun en tepesine yakınsa Alıcı Baskısı (Aggressive Buyers),
        Eğer kapanış mumun en dibine yakınsa Satıcı Baskısı (Aggressive Sellers).
        (Close - Low) / (High - Low)
        """
        if df.empty or len(df) < window:
            return pd.Series(dtype=float)
            
        bar_range = df['high'] - df['low']
        # 0'a bölmeyi engelle
        bar_range = np.where(bar_range == 0, 0.0001, bar_range)
        
        close_location = (df['close'] - df['low']) / bar_range
        
        # Son X mumun ortalama kapanış konumu (Örn: > 0.6 ise Alıcı baskın, < 0.4 ise Satıcı)
        imbalance = pd.Series(close_location).rolling(window=window).mean()
        return imbalance

    @staticmethod
    def detect_liquidity_sweeps(df: pd.DataFrame, lookback: int = 20) -> List[Dict[str, Any]]:
        """
        Stop Patlatma / Likidite Avı (Liquidity Sweep).
        Eski diplerin veya tepelerin altına/üstüne uzun iğne (Wick) atıp 
        hızlıca geri çekilen mumları tespit eder.
        """
        sweeps = []
        if df.empty or len(df) < lookback:
            return sweeps
            
        # Basitçe son X gün içindeki pin barları / uzun iğneleri arıyoruz.
        for i in range(lookback, len(df)):
            current = df.iloc[i]
            
            # Üst İğne (Upper Wick) ve Alt İğne (Lower Wick)
            body_top = max(current['open'], current['close'])
            body_bottom = min(current['open'], current['close'])
            
            upper_wick = current['high'] - body_top
            lower_wick = body_bottom - current['low']
            body_size = body_top - body_bottom
            total_range = current['high'] - current['low']
            
            if total_range == 0:
                continue
                
            # Alt Likidite Avı (Bullish Sweep - Stop Patlatma)
            # Eğer alt iğne gövdeden 2 kat büyükse ve son 20 barın en düşük seviyesine iğne atıp kapatmışsa
            recent_low = df['low'].iloc[i-lookback:i].min()
            if current['low'] <= recent_low and lower_wick > (body_size * 2) and lower_wick > (total_range * 0.5):
                sweeps.append({
                    "Date": df.index[i].strftime("%Y-%m-%d") if isinstance(df.index, pd.DatetimeIndex) else str(i),
                    "Type": "BULLISH SWEEP (Alt Stoplar Patlatıldı)",
                    "Price_Level": round(current['low'], 2)
                })
                
            # Üst Likidite Avı (Bearish Sweep - Boğa Tuzağı)
            recent_high = df['high'].iloc[i-lookback:i].max()
            if current['high'] >= recent_high and upper_wick > (body_size * 2) and upper_wick > (total_range * 0.5):
                sweeps.append({
                    "Date": df.index[i].strftime("%Y-%m-%d") if isinstance(df.index, pd.DatetimeIndex) else str(i),
                    "Type": "BEARISH SWEEP (Üst Stoplar Patlatıldı / Boğa Tuzağı)",
                    "Price_Level": round(current['high'], 2)
                })
                
        return sweeps

    @staticmethod
    def analyze_order_flow(df: pd.DataFrame) -> Dict[str, Any]:
        """Tüm sentetik order flow göstergelerini birleştirir."""
        if df.empty or len(df) < 20:
            return {"error": "Yeterli veri yok."}
            
        imbalance_series = OrderFlowEngine.analyze_synthetic_imbalance(df, window=5)
        latest_imbalance = imbalance_series.iloc[-1]
        
        imbalance_status = "NEUTRAL"
        if latest_imbalance > 0.65:
            imbalance_status = "AGGRESSIVE BUYERS (Yoğun Alış Baskısı)"
        elif latest_imbalance < 0.35:
            imbalance_status = "AGGRESSIVE SELLERS (Yoğun Satış Baskısı)"
            
        sweeps = OrderFlowEngine.detect_liquidity_sweeps(df, lookback=20)
        recent_sweeps = sweeps[-3:] if sweeps else [] # Son 3 tuzak
        
        return {
            "Order_Imbalance_Score": round(latest_imbalance * 100, 1),
            "Order_Imbalance_Status": imbalance_status,
            "Recent_Traps": recent_sweeps,
            "Total_Traps_Found": len(sweeps)
        }
