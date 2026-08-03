import os

CODE_TO_REPLACE = '''    def check_custom_strict_strategy(self, df, direction: str = "AL", lookback_bars: int = 50):
        """
        Scans the last `lookback_bars` to find the MOST RECENT bar where the strategy was fully met.
        Returns: (bool, int, str) -> (is_match, bars_ago, timestamp_str)
        """
        if df.empty or len(df) < 30:
            return False, 0, ""
            
        try:
            import pandas as pd
            import numpy as np
            
            close = df['close'] if 'close' in df.columns else df['Close']
            high = df['high'] if 'high' in df.columns else df['High']
            low = df['low'] if 'low' in df.columns else df['Low']
            
            ema9 = close.ewm(span=9, adjust=False).mean()
            ema21 = close.ewm(span=21, adjust=False).mean()
            
            ema12 = close.ewm(span=12, adjust=False).mean()
            ema26 = close.ewm(span=26, adjust=False).mean()
            macd = ema12 - ema26
            signal = macd.ewm(span=9, adjust=False).mean()
            
            delta = close.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss.replace(0, np.nan)
            rsi = 100 - (100 / (1 + rs))
            
            momentum = close - close.shift(10)
            
            tr1 = high - low
            tr2 = (high - close.shift(1)).abs()
            tr3 = (low - close.shift(1)).abs()
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr = tr.rolling(14).mean()
            
            up = high - high.shift(1)
            down = low.shift(1) - low
            pos_dm = pd.Series(np.where((up > down) & (up > 0), up, 0), index=df.index)
            neg_dm = pd.Series(np.where((down > up) & (down > 0), down, 0), index=df.index)
            pos_di = 100 * (pos_dm.rolling(14).mean() / atr.replace(0, np.nan))
            neg_di = 100 * (neg_dm.rolling(14).mean() / atr.replace(0, np.nan))
            dx = 100 * (abs(pos_di - neg_di) / (pos_di + neg_di).replace(0, np.nan))
            adx = dx.rolling(14).mean()
            
            # Start from the most recent bar and go backwards
            max_idx = len(df) - 1
            start_idx = max(20, max_idx - lookback_bars)
            
            for i in range(max_idx, start_idx - 1, -1):
                c_ema9, c_ema21 = float(ema9.iloc[i]), float(ema21.iloc[i])
                c_macd, c_signal = float(macd.iloc[i]), float(signal.iloc[i])
                c_rsi = float(rsi.iloc[i])
                c_mom = float(momentum.iloc[i])
                c_adx = float(adx.iloc[i])
                
                # Check slippage for the 3 bars ending at i
                crossed_recently = False
                for j in range(i, max(0, i-3) - 1, -1):
                    p_rsi = float(rsi.iloc[j-1])
                    curr_rsi = float(rsi.iloc[j])
                    p_mom = float(momentum.iloc[j-1])
                    curr_mom = float(momentum.iloc[j])
                    
                    if direction == "AL":
                        if p_rsi <= 50 and curr_rsi > 50: crossed_recently = True
                        if p_mom <= 0 and curr_mom > 0: crossed_recently = True
                    elif direction == "SAT":
                        if p_rsi >= 50 and curr_rsi < 50: crossed_recently = True
                        if p_mom >= 0 and curr_mom < 0: crossed_recently = True
                
                if direction == "AL":
                    if c_adx > 25 and c_mom > 0 and c_rsi > 50 and c_macd > c_signal and c_ema9 > c_ema21 and crossed_recently:
                        bars_ago = max_idx - i
                        timestamp_str = str(df.index[i])
                        return True, bars_ago, timestamp_str
                elif direction == "SAT":
                    if c_adx > 25 and c_mom < 0 and c_rsi < 50 and c_macd < c_signal and c_ema9 < c_ema21 and crossed_recently:
                        bars_ago = max_idx - i
                        timestamp_str = str(df.index[i])
                        return True, bars_ago, timestamp_str
                        
            return False, 0, ""
                
        except Exception as e:
            return False, 0, ""'''

with open(r'C:\Users\nebio\Desktop\VarantRadarPro\analysis\technical.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if 'def check_custom_strict_strategy' in line:
        start_idx = i
        break

lines = lines[:start_idx]
lines.append(CODE_TO_REPLACE)
with open(r'C:\Users\nebio\Desktop\VarantRadarPro\analysis\technical.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)
