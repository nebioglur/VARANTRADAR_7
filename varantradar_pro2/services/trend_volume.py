import pandas as pd
import numpy as np

class TrendVolumeAnalyzer:
    @staticmethod
    def analyze_trend(df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculates Short, Medium, and Long-term trends and overall Trend Score.
        """
        if df.empty or len(df) < 200:
            return df
            
        # Short Term: EMA 20 vs EMA 50
        df['EMA_20'] = df['close'].ewm(span=20, adjust=False).mean()
        df['EMA_50'] = df['close'].ewm(span=50, adjust=False).mean()
        df['Trend_Short'] = np.where(df['EMA_20'] > df['EMA_50'], 1, -1)
        
        # Medium Term: SMA 50 vs SMA 100
        df['SMA_50'] = df['close'].rolling(window=50).mean()
        df['SMA_100'] = df['close'].rolling(window=100).mean()
        df['Trend_Medium'] = np.where(df['SMA_50'] > df['SMA_100'], 1, -1)
        
        # Long Term: SMA 100 vs SMA 200
        df['SMA_200'] = df['close'].rolling(window=200).mean()
        df['Trend_Long'] = np.where(df['SMA_100'] > df['SMA_200'], 1, -1)
        
        # Trend Score (from -3 to +3)
        df['Trend_Score'] = df['Trend_Short'] + df['Trend_Medium'] + df['Trend_Long']
        
        # Trend Strength based on ADX (requires pandas_ta ADX to be calculated in analyzer)
        if 'ADX_14' in df.columns:
            df['Trend_Strength'] = df['ADX_14']
        else:
            df['Trend_Strength'] = 0.0
            
        return df

    @staticmethod
    def analyze_volume(df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculates Volume metrics and Money Flow (OBV).
        """
        if df.empty or len(df) < 20:
            return df
            
        # Average Volume (20 days)
        df['Vol_SMA_20'] = df['volume'].rolling(window=20).mean()
        
        # Volume Change (%)
        df['Vol_Change_Pct'] = (df['volume'] / df['Vol_SMA_20']) * 100
        
        # Money Flow (On-Balance Volume - OBV calculation)
        obv = [0]
        for i in range(1, len(df)):
            if df['close'].iloc[i] > df['close'].iloc[i-1]:
                obv.append(obv[-1] + df['volume'].iloc[i])
            elif df['close'].iloc[i] < df['close'].iloc[i-1]:
                obv.append(obv[-1] - df['volume'].iloc[i])
            else:
                obv.append(obv[-1])
                
        df['OBV'] = obv
        
        # OBV Trend
        df['OBV_SMA_20'] = df['OBV'].rolling(window=20).mean()
        df['Money_Flow_Status'] = np.where(df['OBV'] > df['OBV_SMA_20'], "Inflow", "Outflow")
        
        return df
