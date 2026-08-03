import pandas as pd
import numpy as np

class SupportResistanceAnalyzer:
    @staticmethod
    def calculate_pivot_points(df: pd.DataFrame) -> pd.DataFrame:
        """ Calculates classic Pivot Points, Support 1-3, Resistance 1-3 """
        if df.empty or len(df) < 2:
            return df
            
        prev_high = df['high'].shift(1)
        prev_low = df['low'].shift(1)
        prev_close = df['close'].shift(1)
        
        df['Pivot'] = (prev_high + prev_low + prev_close) / 3
        df['R1'] = (2 * df['Pivot']) - prev_low
        df['S1'] = (2 * df['Pivot']) - prev_high
        df['R2'] = df['Pivot'] + (prev_high - prev_low)
        df['S2'] = df['Pivot'] - (prev_high - prev_low)
        df['R3'] = prev_high + 2 * (df['Pivot'] - prev_low)
        df['S3'] = prev_low - 2 * (prev_high - df['Pivot'])
        
        return df

    @staticmethod
    def detect_swing_high_low(df: pd.DataFrame, window: int = 5) -> pd.DataFrame:
        """ Detects local tops and bottoms (Swings) """
        if df.empty:
            return df
            
        df['Swing_High'] = df['high'] == df['high'].rolling(window=window*2+1, center=True).max()
        df['Swing_Low'] = df['low'] == df['low'].rolling(window=window*2+1, center=True).min()
        
        return df

    @staticmethod
    def calculate_fibonacci(df: pd.DataFrame, period: int = 252) -> pd.DataFrame:
        """ Fibonacci Retracement Levels for a given period (default 1 year = 252 days) """
        if len(df) < period:
            period = len(df)
            
        max_price = df['high'].rolling(window=period).max()
        min_price = df['low'].rolling(window=period).min()
        diff = max_price - min_price
        
        df['FIB_0.0'] = max_price
        df['FIB_23.6'] = max_price - diff * 0.236
        df['FIB_38.2'] = max_price - diff * 0.382
        df['FIB_50.0'] = max_price - diff * 0.500
        df['FIB_61.8'] = max_price - diff * 0.618
        df['FIB_78.6'] = max_price - diff * 0.786
        df['FIB_100.0'] = min_price
        
        return df

    @staticmethod
    def auto_support_resistance(df: pd.DataFrame, bins: int = 50) -> pd.DataFrame:
        """ KMeans veya Histogram bazlı en çok temas edilen fiyat seviyeleri (Otomatik D/D) """
        # Basitleştirilmiş Histogram (Volume Profile/Price Profile) mantığı
        if len(df) > 50:
            prices = df['close'].tail(252).values # Son 1 yıl
            hist, bin_edges = np.histogram(prices, bins=bins)
            # En çok yığılma olan tepeleri bul
            top_bins = np.argsort(hist)[-5:] # En yoğun 5 seviye
            
            # DataFrame'e sabit kolonlar olarak ekle (Çizim için)
            for i, b in enumerate(top_bins):
                level_price = (bin_edges[b] + bin_edges[b+1]) / 2
                df[f'AUTO_SR_{i+1}'] = level_price
        return df

    @staticmethod
    def detect_breakout(df: pd.DataFrame, lookback: int = 20) -> pd.DataFrame:
        """ Fiyatın önceki N çubuğun zirvesini kırması veya dibini kırması (Breakout/Fakeout) """
        df['Rolling_High'] = df['high'].shift(1).rolling(lookback).max()
        df['Rolling_Low'] = df['low'].shift(1).rolling(lookback).min()
        
        df['Breakout_Up'] = df['close'] > df['Rolling_High']
        df['Breakout_Down'] = df['close'] < df['Rolling_Low']
        
        # Fake Breakout: Gün içinde kırıp kapanışta altında kalması
        df['Fakeout_Up'] = (df['high'] > df['Rolling_High']) & (df['close'] < df['Rolling_High'])
        df['Fakeout_Down'] = (df['low'] < df['Rolling_Low']) & (df['close'] > df['Rolling_Low'])
        
        return df
