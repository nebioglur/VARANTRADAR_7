import os

CODE_TO_REPLACE = '''    def check_custom_strict_strategy(self, df, direction: str = "AL") -> bool:
        """
        User Custom Strict Strategy (Tolerant Slippage):
        Trigger: RSI crosses 50
        Support: ADX > 25, Momentum > 0, MACD > Signal, EMA 9 > EMA 21
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
            current_ema9 = float(ema9.iloc[-1])
            current_ema21 = float(ema21.iloc[-1])
            
            # 2. MACD
            ema12 = close.ewm(span=12, adjust=False).mean()
            ema26 = close.ewm(span=26, adjust=False).mean()
            macd = ema12 - ema26
            signal = macd.ewm(span=9, adjust=False).mean()
            current_macd = float(macd.iloc[-1])
            current_signal = float(signal.iloc[-1])
            
            # 3. RSI
            delta = close.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss.replace(0, np.nan)
            rsi = 100 - (100 / (1 + rs))
            current_rsi = float(rsi.iloc[-1])
            prev_rsi = float(rsi.iloc[-2]) if len(rsi) > 1 else current_rsi
            
            # 4. Momentum (10 bar)
            momentum = close - close.shift(10)
            current_momentum = float(momentum.iloc[-1])
            
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
            current_adx = float(adx.iloc[-1])
            
            # Evaluate Conditions (RSI Trigger, others support)
            if direction == "AL":
                if not (prev_rsi <= 50 and current_rsi > 50): return False # STRICT TRIGGER
                if current_adx <= 25: return False # SUPPORT
                if current_momentum <= 0: return False # SUPPORT
                if current_macd <= current_signal: return False # SUPPORT
                if current_ema9 <= current_ema21: return False # SUPPORT
                return True
                
            elif direction == "SAT":
                if not (prev_rsi >= 50 and current_rsi < 50): return False # STRICT TRIGGER
                if current_adx <= 25: return False # SUPPORT (ADX is trend strength, must be > 25 for strong downtrend)
                if current_momentum >= 0: return False # SUPPORT
                if current_macd >= current_signal: return False # SUPPORT
                if current_ema9 >= current_ema21: return False # SUPPORT
                return True
                
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
