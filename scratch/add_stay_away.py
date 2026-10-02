import re

with open('analysis/technical.py', 'r', encoding='utf-8') as f:
    c = f.read()

new_method = """
    def analyze_1h_stay_away(self, symbol: str, data: Any = None) -> Dict[str, Any]:
        \"\"\"
        1 Saatlik (1h) veriler üzerinde UZAK DUR (Stay Away / Negatif Momentum) analizi yapar.
        analyze_1h_opportunities metodunun tam tersidir.
        \"\"\"
        import math
        import pandas as pd
        import numpy as np
        
        if data is None or not isinstance(data, pd.DataFrame) or data.empty or len(data) < 20:
            return None
            
        df = data.copy()
        close_col = 'close' if 'close' in df.columns else 'Close'
        high_col = 'high' if 'high' in df.columns else 'High'
        low_col = 'low' if 'low' in df.columns else 'Low'
        
        try:
            close = df[close_col]
            high = df[high_col]
            low = df[low_col]
            
            # EMA
            ema8 = close.ewm(span=8, adjust=False).mean()
            ema21 = close.ewm(span=21, adjust=False).mean()
            
            # MACD
            ema12 = close.ewm(span=12, adjust=False).mean()
            ema26 = close.ewm(span=26, adjust=False).mean()
            macd = ema12 - ema26
            macd_signal = macd.ewm(span=9, adjust=False).mean()
            
            # RSI
            delta = close.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss.replace(0, np.nan)
            rsi = 100 - (100 / (1 + rs))
            
            # ADX
            up = high.diff()
            down = low.shift(1) - low
            plus_dm = pd.Series(np.where((up > down) & (up > 0), up, 0.0), index=df.index)
            minus_dm = pd.Series(np.where((down > up) & (down > 0), down, 0.0), index=df.index)
            
            tr1 = high - low
            tr2 = (high - close.shift(1)).abs()
            tr3 = (low - close.shift(1)).abs()
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            
            atr = tr.ewm(alpha=1/14, adjust=False).mean()
            plus_di = 100 * (plus_dm.ewm(alpha=1/14, adjust=False).mean() / atr)
            minus_di = 100 * (minus_dm.ewm(alpha=1/14, adjust=False).mean() / atr)
            dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
            adx = dx.ewm(alpha=1/14, adjust=False).mean()
            
            # Momentum
            momentum = close - close.shift(10)
            
            c_ema8 = float(ema8.iloc[-1])
            c_ema21 = float(ema21.iloc[-1])
            c_macd = float(macd.iloc[-1])
            c_macd_sig = float(macd_signal.iloc[-1])
            c_rsi = float(rsi.iloc[-1])
            c_adx = float(adx.iloc[-1])
            c_plus_di = float(plus_di.iloc[-1])
            c_minus_di = float(minus_di.iloc[-1])
            c_mom = float(momentum.iloc[-1])
            
            # Negatif Koşullar (Ayı Piyasası)
            cond_ema = c_ema8 < c_ema21
            cond_macd = c_macd < c_macd_sig
            cond_rsi = c_rsi < 50
            cond_adx = c_adx > 20 and c_minus_di > c_plus_di
            cond_mom = c_mom < 0
            
            score_out_of_5 = sum([cond_ema, cond_macd, cond_rsi, cond_adx, cond_mom])
            
            current_price = float(close.iloc[-1])
            
            # Son 20 bar içinde aşağı yönlü kesişim olmuş mu?
            ema_diff = ema8 - ema21
            crossover_found = False
            crossover_bars_ago = -1
            lookback = min(21, len(ema_diff))
            
            for i in range(1, lookback):
                idx_now = len(ema_diff) - i
                idx_prev = idx_now - 1
                if idx_prev >= 0:
                    val_now = float(ema_diff.iloc[idx_now])
                    val_prev = float(ema_diff.iloc[idx_prev])
                    # Önceki barda EMA8 >= EMA21, bu barda EMA8 < EMA21 (Aşağı kesişim)
                    if val_now < 0 and val_prev >= 0:
                        crossover_found = True
                        crossover_bars_ago = i
                        break
            
            if not crossover_found:
                return None
                
            gap = c_ema21 - c_ema8 # Arayı açmış mı (negatif yönde)
            gap_pct = 0.0
            if current_price > 0 and not math.isnan(current_price) and not math.isnan(gap):
                gap_pct = (gap / current_price) * 100
                
            if math.isnan(gap_pct): gap_pct = 0.0
            
            # Düşüş yönlü kesişim belirgin olmalı
            if gap_pct < 0.2:
                return None
                
            daily_change_pct = 0.0
            if not df.empty and hasattr(df.index, 'date'):
                try:
                    current_date = df.index[-1].date()
                    prev_days = df[df.index.date < current_date]
                    if not prev_days.empty:
                        prev_close = float(prev_days[close_col].iloc[-1])
                        if prev_close > 0 and not math.isnan(prev_close) and not math.isnan(current_price):
                            daily_change_pct = ((current_price - prev_close) / prev_close) * 100
                except Exception:
                    pass

            if math.isnan(daily_change_pct): daily_change_pct = 0.0
            if math.isnan(current_price): current_price = 0.0
            if math.isnan(c_rsi): c_rsi = 0.0
            if math.isnan(c_adx): c_adx = 0.0
            
            return {
                "Symbol": symbol,
                "Score_5": int(score_out_of_5),
                "EMA_Gap_Pct": round(gap_pct, 2),
                "Daily_Change_Pct": round(daily_change_pct, 2),
                "Crossover_Bars_Ago": crossover_bars_ago,
                "Price": round(current_price, 2),
                "EMA_Match": bool(cond_ema),
                "MACD_Match": bool(cond_macd),
                "RSI_Match": bool(cond_rsi),
                "ADX_Match": bool(cond_adx),
                "MOM_Match": bool(cond_mom),
                "RSI_Val": round(c_rsi, 1),
                "ADX_Val": round(c_adx, 1)
            }
            
        except Exception as e:
            return None

    def check_custom_strict_strategy"""

if 'def analyze_1h_stay_away' not in c:
    c = c.replace('    def check_custom_strict_strategy', new_method)
    with open('analysis/technical.py', 'w', encoding='utf-8') as f:
        f.write(c)
    print('SUCCESS')
else:
    print('ALREADY ADDED')
