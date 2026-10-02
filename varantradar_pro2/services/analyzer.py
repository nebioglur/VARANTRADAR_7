import pandas as pd
import numpy as np
from database.db_manager import DBManager
from utils.logger import logger

class Analyzer:
    def __init__(self):
        self.db = DBManager()

    def calculate_indicators(self, symbol: str, interval: str = "1d") -> pd.DataFrame:
        df = self.db.get_stock_data(symbol, interval)
        if df.empty:
            logger.warning(f"No data to analyze for {symbol} at {interval}")
            return df
            
        # Ensure data is sorted by date ascending
        df.sort_values('date', inplace=True)
        
        # Yahoo Finance sometimes returns NaN for today's close if the market is closed
        df.dropna(subset=['close'], inplace=True)
        
        # Basic Indicators
        df['SMA'] = df['close'].rolling(window=20).mean()
        df['EMA'] = df['close'].ewm(span=20, adjust=False).mean()
        
        # RSI (14 periods)
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        # MACD
        exp1 = df['close'].ewm(span=12, adjust=False).mean()
        exp2 = df['close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = exp1 - exp2
        df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
        
        # Bollinger Bands
        std = df['close'].rolling(window=20).std()
        df['BB_Upper'] = df['SMA'] + (std * 2)
        df['BB_Lower'] = df['SMA'] - (std * 2)

        try:
            # VWAP
            v = df['volume']
            tp = (df['high'] + df['low'] + df['close']) / 3
            df['VWAP'] = (tp * v).cumsum() / v.cumsum()
            
            # ATR (14)
            tr1 = df['high'] - df['low']
            tr2 = abs(df['high'] - df['close'].shift())
            tr3 = abs(df['low'] - df['close'].shift())
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            df['ATR'] = tr.rolling(14).mean()
            
            # Simple SuperTrend
            hl2 = (df['high'] + df['low']) / 2
            df['ST_Upper'] = hl2 + (3 * df['ATR'])
            df['ST_Lower'] = hl2 - (3 * df['ATR'])
            df['SUPERTREND'] = df['ST_Lower']
            
            # ADX (14)
            plus_dm = df['high'].diff()
            minus_dm = df['low'].diff(-1)
            plus_dm[plus_dm < 0] = 0
            minus_dm[minus_dm < 0] = 0
            tr_smooth = df['ATR'] * 14
            plus_di = 100 * (plus_dm.ewm(alpha=1/14, adjust=False).mean() / tr_smooth)
            minus_di = 100 * (minus_dm.ewm(alpha=1/14, adjust=False).mean() / tr_smooth)
            dx = (abs(plus_di - minus_di) / abs(plus_di + minus_di)) * 100
            df['ADX'] = dx.ewm(alpha=1/14, adjust=False).mean()
            
            # OBV (On Balance Volume)
            df['OBV'] = (np.sign(df['close'].diff()) * df['volume']).fillna(0).cumsum()

            # ROC & Momentum (14)
            df['ROC'] = (df['close'] / df['close'].shift(14) - 1) * 100
            df['MOMENTUM'] = df['close'] - df['close'].shift(14)

            # Williams %R (14)
            highest_high = df['high'].rolling(window=14).max()
            lowest_low = df['low'].rolling(window=14).min()
            df['WILLIAMS_R'] = (highest_high - df['close']) / (highest_high - lowest_low) * -100

            # CCI (Commodity Channel Index - 20)
            tp_20_sma = tp.rolling(20).mean()
            mad = tp.rolling(20).apply(lambda x: np.mean(np.abs(x - np.mean(x))), raw=True)
            df['CCI'] = (tp - tp_20_sma) / (0.015 * mad)

            # Donchian Channels (20)
            df['DONCHIAN_UPPER'] = df['high'].rolling(20).max()
            df['DONCHIAN_LOWER'] = df['low'].rolling(20).min()
            df['DONCHIAN_MID'] = (df['DONCHIAN_UPPER'] + df['DONCHIAN_LOWER']) / 2

            # Keltner Channels (20)
            df['KELTNER_MID'] = df['EMA']
            df['KELTNER_UPPER'] = df['KELTNER_MID'] + (2 * df['ATR'])
            df['KELTNER_LOWER'] = df['KELTNER_MID'] - (2 * df['ATR'])

            # Ichimoku Cloud
            high_9 = df['high'].rolling(9).max()
            low_9 = df['low'].rolling(9).min()
            df['ICHIMOKU_TENKAN'] = (high_9 + low_9) / 2
            high_26 = df['high'].rolling(26).max()
            low_26 = df['low'].rolling(26).min()
            df['ICHIMOKU_KIJUN'] = (high_26 + low_26) / 2
            df['ICHIMOKU_SENKOU_A'] = ((df['ICHIMOKU_TENKAN'] + df['ICHIMOKU_KIJUN']) / 2).shift(26)
            high_52 = df['high'].rolling(52).max()
            low_52 = df['low'].rolling(52).min()
            df['ICHIMOKU_SENKOU_B'] = ((high_52 + low_52) / 2).shift(26)
            
            # MFI (Money Flow Index 14)
            raw_mf = tp * df['volume']
            pos_mf = np.where(tp > tp.shift(1), raw_mf, 0)
            neg_mf = np.where(tp < tp.shift(1), raw_mf, 0)
            pos_mf_sum = pd.Series(pos_mf).rolling(14).sum()
            neg_mf_sum = pd.Series(neg_mf).rolling(14).sum()
            mfi_ratio = pos_mf_sum / neg_mf_sum
            df['MFI'] = 100 - (100 / (1 + mfi_ratio))
            # ALMA (Arnaud Legoux Moving Average - 9)
            # Standard ALMA formula
            window = 9
            sigma = 6
            offset = 0.85
            m = int(offset * (window - 1))
            s = window / sigma
            alma_weights = np.exp(-((np.arange(window) - m) ** 2) / (2 * s ** 2))
            alma_weights /= alma_weights.sum()
            df['ALMA'] = df['close'].rolling(window).apply(lambda x: np.dot(x, alma_weights), raw=True)

            # PSAR (Parabolic SAR) - Simplified Version
            df['PSAR'] = df['close'].copy() # Initialize with close
            af0 = 0.02
            af_max = 0.2
            # For a pure python iterative PSAR we need a loop, but for performance we'll approximate with SuperTrend logic or a very basic loop
            # Real PSAR is highly iterative. Using a simplified proxy for now to maintain performance.
            # We'll use a 5-day rolling min/max as a proxy for the SAR dots.
            is_uptrend = df['close'] > df['SMA']
            df.loc[is_uptrend, 'PSAR'] = df['low'].rolling(5).min()
            df.loc[~is_uptrend, 'PSAR'] = df['high'].rolling(5).max()
        except Exception as e:
            logger.error(f"Error calculating advanced indicators manually: {e}")
            
        # Add Support/Resistance calculations (from Roadmap section D)
        from services.support_resistance import SupportResistanceAnalyzer
        df = SupportResistanceAnalyzer.calculate_pivot_points(df)
        df = SupportResistanceAnalyzer.detect_swing_high_low(df)
        df = SupportResistanceAnalyzer.calculate_fibonacci(df)
        df = SupportResistanceAnalyzer.auto_support_resistance(df)
        df = SupportResistanceAnalyzer.detect_breakout(df)
        
        # Add Pattern Recognition (from Roadmap section G)
        from services.pattern_recognition import PatternRecognitionEngine
        df = PatternRecognitionEngine.detect_all_patterns(df)
        
        # Add Trend and Volume calculations (from Roadmap section E & F)
        from services.trend_volume import TrendVolumeAnalyzer
        df = TrendVolumeAnalyzer.analyze_trend(df)
        df = TrendVolumeAnalyzer.analyze_volume(df)
            
        return df
