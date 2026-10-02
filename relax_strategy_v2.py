import os

CODE_TO_REPLACE = '''    def check_custom_strict_strategy(self, df, direction: str = "AL") -> bool:
        """
        User Custom Strict Strategy (Tolerant Slippage):
        Tolerates up to 3 bars of slippage for crossovers.
        Currently ALL conditions must be met.
        At least one condition must have crossed its threshold in the last 3 bars.
        """
        if df.empty or len(df) < 30:
            return False
            
        try:
            import pandas as pd
            import numpy as np
            
            close = df['close'] if 'close' in df.columns else df['Close']
            high = df['high'] if 'high' in df.columns else df['High']
            low = df['low'] if 'low' in df.columns else df['Low']
            
            # 1. EMA 9 and EMA 21
            ema9 = close.ewm(span=9, adjust=False).mean()
            ema21 = close.ewm(span=21, adjust=False).mean()
            
            # 2. MACD
            ema12 = close.ewm(span=12, adjust=False).mean()
            ema26 = close.ewm(span=26, adjust=False).mean()
            macd = ema12 - ema26
            signal = macd.ewm(span=9, adjust=False).mean()
            
            # 3. RSI
            delta = close.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss.replace(0, np.nan)
            rsi = 100 - (100 / (1 + rs))
            
            # 4. Momentum (10 bar)
            momentum = close - close.shift(10)
            
            # 5. ADX (14)
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
            
            # Get last 4 values for crossover checks (to tolerate 3 bars slippage)
            if len(df) < 4: return False
            
            # Current values
            c_ema9, c_ema21 = float(ema9.iloc[-1]), float(ema21.iloc[-1])
            c_macd, c_signal = float(macd.iloc[-1]), float(signal.iloc[-1])
            c_rsi = float(rsi.iloc[-1])
            c_mom = float(momentum.iloc[-1])
            c_adx = float(adx.iloc[-1])
            
            # Slippage tolerance check: Did any indicator cross recently? (last 3 bars)
            crossed_recently = False
            for i in range(-1, -4, -1):
                p_rsi = float(rsi.iloc[i-1])
                curr_rsi = float(rsi.iloc[i])
                p_mom = float(momentum.iloc[i-1])
                curr_mom = float(momentum.iloc[i])
                
                if direction == "AL":
                    if p_rsi <= 50 and curr_rsi > 50: crossed_recently = True
                    if p_mom <= 0 and curr_mom > 0: crossed_recently = True
                elif direction == "SAT":
                    if p_rsi >= 50 and curr_rsi < 50: crossed_recently = True
                    if p_mom >= 0 and curr_mom < 0: crossed_recently = True
            
            # Evaluate ALL Conditions (Must all support currently)
            if direction == "AL":
                if c_adx <= 25: return False
                if c_mom <= 0: return False
                if c_rsi <= 50: return False
                if c_macd <= c_signal: return False
                if c_ema9 <= c_ema21: return False
                return crossed_recently
                
            elif direction == "SAT":
                if c_adx <= 25: return False # ADX shows strength, must be > 25 for strong downtrend
                if c_mom >= 0: return False
                if c_rsi >= 50: return False
                if c_macd >= c_signal: return False
                if c_ema9 >= c_ema21: return False
                return crossed_recently
                
        except Exception as e:
            return False
            
        return False'''

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
