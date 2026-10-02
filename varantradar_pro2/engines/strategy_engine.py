import pandas as pd
import numpy as np
from typing import Callable, Dict

class StrategyEngine:
    """
    Kullanıcı veya AI tarafından seçilen stratejilerin (EMA, RSI, MACD) vektörel olarak 
    sinyal (1 = Al, 0 = Bekle, -1 = Sat) üretmesini sağlar.
    """
    
    @staticmethod
    def get_available_strategies() -> Dict[str, Callable]:
        return {
            "EMA_Crossover": StrategyEngine.ema_crossover,
            "RSI_Reversal": StrategyEngine.rsi_reversal,
            "MACD_Trend": StrategyEngine.macd_trend
        }

    @staticmethod
    def ema_crossover(df: pd.DataFrame, fast_period: int = 20, slow_period: int = 50) -> pd.Series:
        """Fast EMA yukarı keserse Al (1), aşağı keserse Sat (-1)."""
        fast = df['close'].ewm(span=fast_period, adjust=False).mean()
        slow = df['close'].ewm(span=slow_period, adjust=False).mean()
        
        signals = pd.Series(0, index=df.index)
        
        # Kesim noktalarını bulma (vektörel)
        bullish = (fast > slow) & (fast.shift(1) <= slow.shift(1))
        bearish = (fast < slow) & (fast.shift(1) >= slow.shift(1))
        
        signals[bullish] = 1
        signals[bearish] = -1
        return signals

    @staticmethod
    def rsi_reversal(df: pd.DataFrame, period: int = 14, overbought: int = 70, oversold: int = 30) -> pd.Series:
        """RSI aşırı satımdan çıkarken Al (1), aşırı alımdan çıkarken Sat (-1)."""
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        signals = pd.Series(0, index=df.index)
        
        # RSI 30'u yukarı keserse AL
        bullish = (rsi > oversold) & (rsi.shift(1) <= oversold)
        # RSI 70'i aşağı keserse SAT
        bearish = (rsi < overbought) & (rsi.shift(1) >= overbought)
        
        signals[bullish] = 1
        signals[bearish] = -1
        return signals

    @staticmethod
    def macd_trend(df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.Series:
        """MACD, Sinyal hattını yukarı keserse AL, aşağı keserse SAT."""
        ema_fast = df['close'].ewm(span=fast, adjust=False).mean()
        ema_slow = df['close'].ewm(span=slow, adjust=False).mean()
        macd = ema_fast - ema_slow
        macd_signal = macd.ewm(span=signal, adjust=False).mean()
        
        signals = pd.Series(0, index=df.index)
        bullish = (macd > macd_signal) & (macd.shift(1) <= macd_signal.shift(1))
        bearish = (macd < macd_signal) & (macd.shift(1) >= macd_signal.shift(1))
        
        signals[bullish] = 1
        signals[bearish] = -1
        return signals
