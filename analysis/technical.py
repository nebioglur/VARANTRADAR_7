import pandas as pd
import numpy as np
import math
from datetime import datetime, timedelta
from typing import Dict, Any, Union
from core.interfaces import BaseEngine

class TechnicalEngine(BaseEngine):
    """
    CFG-04 Analysis Architecture (Technical Core)
    Fiyat hareketlerinin mekaniğini (Trend ve Momentum) analiz eder.
    BaseEngine standartlarına uygun (0-100) skor döner.
    """
    
    def analyze(self, symbol: str, data: Any = None) -> Dict[str, Union[float, str]]:
        result = {
            "Score": 50.0,
            "Status": "UNKNOWN",
            "Trend": "UNKNOWN",
            "Momentum": "UNKNOWN",
            "Analysis": "Yetersiz Veri"
        }
        
        if data is None or not isinstance(data, pd.DataFrame) or data.empty or len(data) < 50:
            self.validate_output(result)
            return result
            
        df = data
        close = df['close'] if 'close' in df.columns else df['Close']
        
        try:
            # 1. Trend Tanıma (Hareketli Ortalamalar)
            ema20 = close.ewm(span=20, adjust=False).mean()
            ema50 = close.ewm(span=50, adjust=False).mean()
            ema200 = close.ewm(span=200, adjust=False).mean()
            
            c = close.iloc[-1]
            e20 = ema20.iloc[-1]
            e50 = ema50.iloc[-1]
            e200 = ema200.iloc[-1]
            
            trend_score = 0
            trend_status = "YATAY"
            
            if c > e20 and e20 > e50 and e50 > e200:
                trend_score = 100
                trend_status = "GÜÇLÜ YÜKSELİŞ"
            elif c > e20 and e20 > e50:
                trend_score = 75
                trend_status = "YÜKSELİŞ"
            elif c < e20 and e20 < e50 and e50 < e200:
                trend_score = 0
                trend_status = "GÜÇLÜ DÜŞÜŞ"
            elif c < e20 and e20 < e50:
                trend_score = 25
                trend_status = "DÜŞÜŞ"
            else:
                trend_score = 50
                trend_status = "YATAY"
                
            # 2. Momentum (RSI)
            delta = close.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss.replace(0, np.nan)
            rsi = 100 - (100 / (1 + rs))
            current_rsi = rsi.iloc[-1]
            
            momentum_score = 50
            momentum_status = "NÖTR"
            
            if pd.notna(current_rsi):
                if current_rsi > 70:
                    momentum_score = 80
                    momentum_status = "AŞIRI ALIM (Overbought)"
                elif current_rsi < 30:
                    momentum_score = 20
                    momentum_status = "AŞIRI SATIM (Oversold)"
                elif current_rsi > 50:
                    momentum_score = 65
                    momentum_status = "POZİTİF"
                else:
                    momentum_score = 35
                    momentum_status = "NEGATİF"
            
            # Kural: Trende karşı Momentum sahtedir (CFG-04)
            final_score = (trend_score * 0.7) + (momentum_score * 0.3)
            
            # RSI şişmiş ama trend düşüşteyse ceza (Fakeout cezası)
            if trend_status == "DÜŞÜŞ" and momentum_status == "AŞIRI ALIM (Overbought)":
                final_score -= 20
                
            final_score = max(0.0, min(100.0, float(final_score)))
            result["Score"] = final_score
            
            if final_score >= 70:
                result["Status"] = "AL"
            elif final_score <= 30:
                result["Status"] = "SAT"
            else:
                result["Status"] = "BEKLE"
                
            result["Trend"] = trend_status
            result["Momentum"] = momentum_status
            result["Indicators"] = {
                "RSI_14": round(current_rsi, 2) if pd.notna(current_rsi) else "N/A",
                "EMA_20": round(e20, 2),
                "EMA_50": round(e50, 2),
                "EMA_200": round(e200, 2)
            }
            
            # --- FAZ 4: MTF (Multi-Timeframe) Analizi ---
            mtf_data = {}
            if isinstance(df.index, pd.DatetimeIndex):
                # Haftalık (W) Resampling
                weekly_df = df.resample('W').agg({'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'}).dropna()
                if not weekly_df.empty:
                    w_c = weekly_df['close']
                    w_ma8 = w_c.rolling(8, min_periods=1).mean().iloc[-1]
                    w_ma21 = w_c.rolling(21, min_periods=1).mean().iloc[-1]
                    w_ma50 = w_c.rolling(50, min_periods=1).mean().iloc[-1]
                    w_ma200 = w_c.rolling(200, min_periods=1).mean().iloc[-1]
                    mtf_data['Weekly'] = {
                        "MA8": round(w_ma8, 2) if pd.notna(w_ma8) else "N/A",
                        "MA21": round(w_ma21, 2) if pd.notna(w_ma21) else "N/A",
                        "MA50": round(w_ma50, 2) if pd.notna(w_ma50) else "N/A",
                        "MA200": round(w_ma200, 2) if pd.notna(w_ma200) else "N/A",
                        "SuperTrend": "YÜKSELİŞ" if w_c.iloc[-1] > (w_ma21 if pd.notna(w_ma21) else 0) else "DÜŞÜŞ"
                    }
                    
                # Aylık (M) Resampling
                monthly_df = df.resample('ME').agg({'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'}).dropna()
                if not monthly_df.empty:
                    m_c = monthly_df['close']
                    m_ma8 = m_c.rolling(8, min_periods=1).mean().iloc[-1]
                    m_ma21 = m_c.rolling(21, min_periods=1).mean().iloc[-1]
                    m_ma50 = m_c.rolling(50, min_periods=1).mean().iloc[-1]
                    m_ma200 = m_c.rolling(200, min_periods=1).mean().iloc[-1]
                    mtf_data['Monthly'] = {
                        "MA8": round(m_ma8, 2) if pd.notna(m_ma8) else "N/A",
                        "MA21": round(m_ma21, 2) if pd.notna(m_ma21) else "N/A",
                        "MA50": round(m_ma50, 2) if pd.notna(m_ma50) else "N/A",
                        "MA200": round(m_ma200, 2) if pd.notna(m_ma200) else "N/A",
                        "SuperTrend": "YÜKSELİŞ" if m_c.iloc[-1] > (m_ma21 if pd.notna(m_ma21) else 0) else "DÜŞÜŞ"
                    }
                    
                # 6 Aylık (6M) Resampling (Kullanıcı Talebi: Faz-4 Unutma)
                semi_annual_df = df.resample('6ME').agg({'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'}).dropna()
                if not semi_annual_df.empty:
                    sa_c = semi_annual_df['close']
                    sa_ma8 = sa_c.rolling(8, min_periods=1).mean().iloc[-1]
                    sa_ma21 = sa_c.rolling(21, min_periods=1).mean().iloc[-1]
                    sa_ma50 = sa_c.rolling(50, min_periods=1).mean().iloc[-1]
                    sa_ma200 = sa_c.rolling(200, min_periods=1).mean().iloc[-1]
                    mtf_data['Month_6'] = {
                        "MA8": round(sa_ma8, 2) if pd.notna(sa_ma8) else "N/A",
                        "MA21": round(sa_ma21, 2) if pd.notna(sa_ma21) else "N/A",
                        "MA50": round(sa_ma50, 2) if pd.notna(sa_ma50) else "N/A",
                        "MA200": round(sa_ma200, 2) if pd.notna(sa_ma200) else "N/A",
                        "SuperTrend": "YÜKSELİŞ" if sa_c.iloc[-1] > (sa_ma21 if pd.notna(sa_ma21) else 0) else "DÜŞÜŞ"
                    }
            result["MTF_Indicators"] = mtf_data
            
            result["Daily_EMA50"] = float(e50)
            result["Daily_EMA200"] = float(e200)
            result["Daily_Close"] = float(c)
            
            result["Analysis"] = f"Trend: {trend_status}, RSI: {round(current_rsi, 2) if pd.notna(current_rsi) else 'N/A'}"
            
        except Exception as e:
            print(f"[TechnicalEngine] Hata: {e}")
            
        self.validate_output(result)
        return result

    def analyze_1h_opportunities(self, symbol: str, data: Any = None) -> Dict[str, Any]:
        """
        1 Saatlik (1h) veriler üzerinde kullanıcının grafikte gördüğü spesifik indikatörlere (EMA 8/21, MACD, RSI, ADX, Momentum)
        dayalı 'Fırsat' analizi yapar. Fırsat şartlarının kaç tanesinin sağlandığını hesaplar.
        """
        if data is None or not isinstance(data, pd.DataFrame) or data.empty or len(data) < 20:
            return None
            
        df = data.copy()
        
        # Standardize columns if necessary
        close_col = 'close' if 'close' in df.columns else 'Close'
        high_col = 'high' if 'high' in df.columns else 'High'
        low_col = 'low' if 'low' in df.columns else 'Low'
        
        try:
            import numpy as np
            
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
            
            # Current Values
            c_ema8 = float(ema8.iloc[-1])
            c_ema21 = float(ema21.iloc[-1])
            c_macd = float(macd.iloc[-1])
            c_macd_sig = float(macd_signal.iloc[-1])
            c_rsi = float(rsi.iloc[-1])
            c_adx = float(adx.iloc[-1])
            c_plus_di = float(plus_di.iloc[-1])
            c_minus_di = float(minus_di.iloc[-1])
            c_mom = float(momentum.iloc[-1])
            
            # Match Conditions
            cond_ema = c_ema8 > c_ema21
            cond_macd = c_macd > c_macd_sig
            cond_rsi = c_rsi > 50
            cond_adx = c_adx > 20 and c_plus_di > c_minus_di
            cond_mom = c_mom > 0
            
            score_out_of_5 = sum([cond_ema, cond_macd, cond_rsi, cond_adx, cond_mom])
            
            # ============================================================
            # 1 Saatlik Fırsat Özel Koşulları (Kullanıcı Kuralı):
            # 1. EMA(8), EMA(21)'i YUKARI KESMİŞ OLACAK (crossover)
            #    Yani önceki barlarda EMA8 <= EMA21 iken, şimdi EMA8 > EMA21
            # 2. Bu kesişim SON 20 SAAT İÇİNDE gerçekleşmiş olacak
            # 3. EMA(8) - EMA(21) >= Fiyatın Binde 2'si (%0.2)
            # AMAÇ: Yeni kesişimleri yakalamak!
            # ============================================================
            
            current_price = float(close.iloc[-1])
            gap = c_ema8 - c_ema21
            
            # Koşul 1 & 2: Son 20 bar içinde crossover olmuş mu?
            # EMA8 - EMA21 farkı serisi oluştur
            ema_diff = ema8 - ema21
            
            # Son 21 bar (şimdiki + 20 önceki) içinde kesişim ara
            # Kesişim = ema_diff'in negatiften pozitife geçtiği nokta
            crossover_found = False
            crossover_bars_ago = -1
            lookback = min(21, len(ema_diff))
            
            for i in range(1, lookback):
                idx_now = len(ema_diff) - i      # şimdiden geriye
                idx_prev = idx_now - 1
                if idx_prev >= 0:
                    val_now = float(ema_diff.iloc[idx_now])
                    val_prev = float(ema_diff.iloc[idx_prev])
                    # Önceki barda EMA8 <= EMA21, bu barda EMA8 > EMA21
                    if val_now > 0 and val_prev <= 0:
                        crossover_found = True
                        crossover_bars_ago = i
                        break
            
            # Crossover yoksa → fırsat yok
            if not crossover_found:
                return None
            
            # Koşul 3: EMA farkı >= fiyatın binde 2'si (%0.2)
            gap_pct = 0.0
            if current_price > 0 and not math.isnan(current_price) and not math.isnan(gap):
                gap_pct = (gap / current_price) * 100
            
            if math.isnan(gap_pct): gap_pct = 0.0
            
            if gap_pct < 0.2:
                return None
                
            # Koşul 4: Hacim artışı -> Son 1 saatlik hacim, son 20 saatin ortalama hacminin en az 1.5 katı olmalı
            vol_col = 'volume' if 'volume' in df.columns else 'Volume'
            if vol_col in df.columns:
                volume = df[vol_col]
                if len(volume) >= 20:
                    current_vol = float(volume.iloc[-1])
                    # Önceki 20 barın ortalaması (şimdiki hariç daha sağlıklı sonuç verir)
                    avg_vol_20 = float(volume.iloc[-21:-1].mean()) if len(volume) > 20 else float(volume.iloc[:-1].mean())
                    if avg_vol_20 > 0 and current_vol < 1.5 * avg_vol_20:
                        return None
                        
                # Koşul 5: OBV (On-Balance Volume) son 20 bar içinde yeni zirve yapmalı
                if len(volume) >= 20:
                    delta_price = close.diff()
                    # Fiyat arttıysa hacim +, düştüyse hacim -, aynıysa 0
                    direction = np.where(delta_price > 0, 1, np.where(delta_price < 0, -1, 0))
                    obv = (direction * volume).cumsum()
                    
                    current_obv = float(obv.iloc[-1])
                    # Son 20 bar içindeki en yüksek OBV değeri (şimdiki dahil)
                    max_obv_20 = float(obv.iloc[-20:].max())
                    
                    # Eğer current_obv, son 20 barın max değerinden küçükse zirve yapmamış demektir
                    if current_obv < max_obv_20:
                        return None
            
            # Günlük Değişim % Hesabı
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
            print(f"[TechnicalEngine 1H] Hata ({symbol}): {e}")
            return None


    @classmethod
    def get_chart_data(cls, symbol: str, interval: str = '1d') -> Dict[str, Any]:
        import yfinance as yf
        import numpy as np
        period_map = {'5m': '5d', '15m': '5d', '1h': '1mo', '4h': '1mo', '1d': '1y', '1wk': '2y', '1mo': '5y'}
        period = period_map.get(interval, '1y')
        df = yf.Ticker(symbol).history(period=period, interval=interval)
        if df.empty:
            return {"status": "error", "message": "No data found"}
            
        close = df['Close']
        high = df['High']
        low = df['Low']
        
        df['EMA9'] = close.ewm(span=9, adjust=False).mean()
        df['EMA21'] = close.ewm(span=21, adjust=False).mean()
        
        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        macd = ema12 - ema26
        macd_signal = macd.ewm(span=9, adjust=False).mean()
        df['MACD'] = macd
        df['MACD_Signal'] = macd_signal
        df['MACD_Hist'] = macd - macd_signal
        
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
        
        df['ADX'] = adx
        df['PLUS_DI'] = plus_di
        df['MINUS_DI'] = minus_di
        
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss.replace(0, np.nan)
        df['RSI'] = 100 - (100 / (1 + rs))
        
        df['Momentum'] = close - close.shift(10)
        
        roll_mean = close.rolling(20).mean()
        roll_std = close.rolling(20).std(ddof=0)
        upper_band = roll_mean + (roll_std * 2)
        lower_band = roll_mean - (roll_std * 2)
        df['BB_P_B'] = (close - lower_band) / (upper_band - lower_band).replace(0, np.nan)
        
        df['ATR'] = atr
        
        # --- Custom SuperTrend Calculation ---
        st_period = 10
        st_multiplier = 3.0
        st_atr = tr.ewm(alpha=1/st_period, adjust=False).mean()
        
        hl2 = (high + low) / 2
        basic_ub = hl2 + (st_multiplier * st_atr)
        basic_lb = hl2 - (st_multiplier * st_atr)
        
        c = close.to_numpy()
        b_ub = basic_ub.to_numpy()
        b_lb = basic_lb.to_numpy()
        
        n = len(c)
        f_ub = np.zeros(n)
        f_lb = np.zeros(n)
        st = np.zeros(n)
        st_dir = np.ones(n) # 1 for up, -1 for down
        
        if n > 0:
            f_ub[0] = b_ub[0]
            f_lb[0] = b_lb[0]
            st[0] = b_lb[0]
            
            for i in range(1, n):
                if b_ub[i] < f_ub[i-1] or c[i-1] > f_ub[i-1]:
                    f_ub[i] = b_ub[i]
                else:
                    f_ub[i] = f_ub[i-1]
                    
                if b_lb[i] > f_lb[i-1] or c[i-1] < f_lb[i-1]:
                    f_lb[i] = b_lb[i]
                else:
                    f_lb[i] = f_lb[i-1]
                    
                if st_dir[i-1] == 1 and c[i] <= f_lb[i]:
                    st_dir[i] = -1
                elif st_dir[i-1] == -1 and c[i] >= f_ub[i]:
                    st_dir[i] = 1
                else:
                    st_dir[i] = st_dir[i-1]
                    
                if st_dir[i] == 1:
                    st[i] = f_lb[i]
                else:
                    st[i] = f_ub[i]
                    
        df['SuperTrend'] = st
        df['SuperTrend_Dir'] = st_dir
        # --- End Custom SuperTrend ---
        
        annotations = []
        for i in range(1, len(df)):
            idx_time = int(df.index[i].timestamp())
            
            # Bools
            has_ema = pd.notna(df['EMA8'].iloc[i]) and pd.notna(df['EMA21'].iloc[i])
            has_macd = pd.notna(df['MACD'].iloc[i]) and pd.notna(df['MACD_Signal'].iloc[i])
            
            ema_cross_up = has_ema and df['EMA8'].iloc[i-1] <= df['EMA21'].iloc[i-1] and df['EMA8'].iloc[i] > df['EMA21'].iloc[i]
            ema_cross_down = has_ema and df['EMA8'].iloc[i-1] >= df['EMA21'].iloc[i-1] and df['EMA8'].iloc[i] < df['EMA21'].iloc[i]
            
            macd_cross_up = has_macd and df['MACD'].iloc[i-1] <= df['MACD_Signal'].iloc[i-1] and df['MACD'].iloc[i] > df['MACD_Signal'].iloc[i]
            macd_cross_down = has_macd and df['MACD'].iloc[i-1] >= df['MACD_Signal'].iloc[i-1] and df['MACD'].iloc[i] < df['MACD_Signal'].iloc[i]
            
            ema_bull = has_ema and df['EMA8'].iloc[i] > df['EMA21'].iloc[i]
            macd_bull = has_macd and df['MACD'].iloc[i] > df['MACD_Signal'].iloc[i]
            ema_bear = has_ema and df['EMA8'].iloc[i] < df['EMA21'].iloc[i]
            macd_bear = has_macd and df['MACD'].iloc[i] < df['MACD_Signal'].iloc[i]
            
            is_strong_macd_up = macd_cross_up and df['MACD'].iloc[i] < 0
            is_strong_macd_down = macd_cross_down and df['MACD'].iloc[i] > 0
            
            # ORTAK AL / SAT
            if (ema_cross_up and macd_bull) or (macd_cross_up and ema_bull):
                annotations.append({"time": idx_time, "position": "belowBar", "color": "#10b981", "shape": "arrowUp", "text": "ORTAK AL", "type": "ortak"})
            elif (ema_cross_down and macd_bear) or (macd_cross_down and ema_bear):
                annotations.append({"time": idx_time, "position": "aboveBar", "color": "#ef4444", "shape": "arrowDown", "text": "ORTAK SAT", "type": "ortak"})
            else:
                if is_strong_macd_up:
                    annotations.append({"time": idx_time, "position": "belowBar", "color": "#3b82f6", "shape": "arrowUp", "text": "DİP MACD AL", "type": "macd"})
                elif is_strong_macd_down:
                    annotations.append({"time": idx_time, "position": "aboveBar", "color": "#f59e0b", "shape": "arrowDown", "text": "TEPE MACD SAT", "type": "macd"})
                    
            # ADX Zone (sadece ortak sinyal yoksa göster ki çok kalabalık olmasın)
            if not ((ema_cross_up and macd_bull) or (macd_cross_up and ema_bull) or is_strong_macd_up):
                if pd.notna(df['ADX'].iloc[i]) and pd.notna(df['PLUS_DI'].iloc[i]):
                    if df['ADX'].iloc[i] > 20 and df['PLUS_DI'].iloc[i] > df['MINUS_DI'].iloc[i] and df['ADX'].iloc[i] > df['ADX'].iloc[i-1]:
                        if df['ADX'].iloc[i-1] <= 20 or df['PLUS_DI'].iloc[i-1] <= df['MINUS_DI'].iloc[i-1]:
                            annotations.append({"time": idx_time, "position": "belowBar", "color": "#eab308", "shape": "arrowUp", "text": "Güçlü Trend", "type": "adx"})
                        
        candles = []
        for idx, row in df.iterrows():
            if interval in ['1d', '1wk', '1mo']:
                time_val = idx.strftime('%Y-%m-%d')
            else:
                # BIST 1h bars in Yahoo Finance often incorrectly start at xx:30 (e.g. 09:30)
                # Shift them to xx:00 (e.g. 10:00) to match exact market hours
                if idx.minute == 30:
                    idx = idx + pd.Timedelta(minutes=30)
                time_val = int(idx.timestamp())
                
            candles.append({
                "time": time_val,
                "open": round(row['Open'], 2),
                "high": round(row['High'], 2),
                "low": round(row['Low'], 2),
                "close": round(row['Close'], 2),
                "volume": float(row['Volume']) if 'Volume' in row else 0,
                "ema8": round(row['EMA8'], 2) if 'EMA8' in row and pd.notna(row.get('EMA8')) else None,
                "ema9": round(row['EMA9'], 2) if 'EMA9' in row and pd.notna(row['EMA9']) else None,
                "ema21": round(row['EMA21'], 2) if pd.notna(row['EMA21']) else None,
                "macd": round(row['MACD'], 2) if pd.notna(row['MACD']) else None,
                "macd_signal": round(row['MACD_Signal'], 2) if pd.notna(row['MACD_Signal']) else None,
                "macd_hist": round(row['MACD_Hist'], 2) if pd.notna(row['MACD_Hist']) else None,
                "adx": round(row['ADX'], 2) if pd.notna(row['ADX']) else None,
                "rsi": round(row['RSI'], 2) if pd.notna(row['RSI']) else None,
                "momentum": round(row['Momentum'], 2) if pd.notna(row['Momentum']) else None,
                "bb_pb": round(row['BB_P_B'], 3) if pd.notna(row['BB_P_B']) else None,
                "atr": round(row['ATR'], 2) if pd.notna(row['ATR']) else None,
                "supertrend": round(row['SuperTrend'], 2) if pd.notna(row['SuperTrend']) else None,
                "supertrend_dir": int(row['SuperTrend_Dir']) if pd.notna(row['SuperTrend_Dir']) else None
            })
            
        # Pivot Points (Macro levels based on the fetched period)
        macro_high = df['High'].max()
        macro_low = df['Low'].min()
        macro_close = df['Close'].iloc[-1]
        
        p = (macro_high + macro_low + macro_close) / 3
        pivots = {
            "P": round(p, 2),
            "R1": round((p * 2) - macro_low, 2),
            "S1": round((p * 2) - macro_high, 2),
            "R2": round(p + (macro_high - macro_low), 2),
            "S2": round(p - (macro_high - macro_low), 2),
            "R3": round(macro_high + 2 * (p - macro_low), 2),
            "S3": round(macro_low - 2 * (macro_high - p), 2)
        }
            
        return {"status": "success", "candles": candles, "annotations": annotations, "pivots": pivots}

    def analyze_tavan_adaylari(self, symbol: str, data: Any = None, daily_stats: Dict = None) -> Dict[str, Any]:
        """
        AI Tavan Olasılığı Skoru (Gizli Tavan Adayı - Gelişmiş Pro Modül)
        1 saatlik veri kullanılarak 1-3 saat önceden yüksek tavan potansiyeli olan hisseleri tespit eder.
        Skor 100 üzerinden hesaplanır.
        """
        if data is None or not isinstance(data, pd.DataFrame) or data.empty or len(data) < 30:
            return None
            
        df = data.copy()
        
        # Standardize columns
        close_col = 'close' if 'close' in df.columns else 'Close'
        open_col = 'open' if 'open' in df.columns else 'Open'
        high_col = 'high' if 'high' in df.columns else 'High'
        low_col = 'low' if 'low' in df.columns else 'Low'
        vol_col = 'volume' if 'volume' in df.columns else 'Volume'
        
        if vol_col not in df.columns or close_col not in df.columns:
            return None
            
        import numpy as np
        
        close = df[close_col]
        open_s = df[open_col] if open_col in df.columns else close
        high = df[high_col]
        low = df[low_col]
        volume = df[vol_col]
        
        current_price = float(close.iloc[-1])
        current_open = float(open_s.iloc[-1])
        current_high = float(high.iloc[-1])
        current_low = float(low.iloc[-1])
        current_vol = float(volume.iloc[-1])
        
        score = 0
        details = []
        
        try:
            # ==========================================
            # 0. Günlük Değişim, Önceki Kapanış ve Kesin BIST Tavanı
            # ==========================================
            prev_close = current_price
            if daily_stats and symbol in daily_stats:
                d_stat = daily_stats[symbol]
                if isinstance(d_stat, dict) and 'Previous_Close' in d_stat and d_stat['Previous_Close']:
                    prev_close = float(d_stat['Previous_Close'])
            
            if prev_close == current_price and hasattr(df.index, 'date'):
                past_dates = df[df.index.date < df.index.date[-1]]
                if not past_dates.empty:
                    prev_close = float(past_dates[close_col].iloc[-1])
            
            # Günlük % Değişim
            change_pct = ((current_price - prev_close) / prev_close) * 100 if prev_close > 0 else 0.0
            
            # Borsa İstanbul Tavanı (%9.95 - %10.00)
            tavan_price = round(prev_close * 1.0995, 2)
            if tavan_price <= current_price:
                tavan_price = round(current_price * 1.0995, 2)
                
            # Tavana Kalan Mesafe (%)
            distance_to_ceiling_pct = ((tavan_price - current_price) / current_price) * 100 if current_price > 0 else 0.0
            distance_to_ceiling_pct = max(0.0, round(distance_to_ceiling_pct, 2))

            # ==========================================
            # 1. Hacim Patlaması & Çarpanı (25 Puan)
            # ==========================================
            avg_vol_20 = float(volume.iloc[-21:-1].mean()) if len(volume) > 20 else float(volume.iloc[:-1].mean())
            vol_multiplier = round(current_vol / avg_vol_20, 1) if avg_vol_20 > 0 else 1.0
            
            if avg_vol_20 > 0:
                if current_vol > avg_vol_20 * 2.5:
                    score += 25
                    details.append(f"🔥 Agresif Hacim Patlaması ({vol_multiplier}x).")
                elif current_vol > avg_vol_20 * 1.5:
                    score += 15
                    details.append(f"Yüksek Hacim Girişi ({vol_multiplier}x).")

            # ==========================================
            # 2. 🛡️ TUZAK ÖNLEYİCİ KALKAN (Anti-Trap Shield) & Mum Gücü
            # ==========================================
            candle_range = current_high - current_low
            candle_body = abs(current_price - current_open)
            upper_wick = current_high - max(current_price, current_open)
            
            trap_risk = False
            candle_strength = "Normal"
            
            if candle_range > 0:
                upper_wick_ratio = upper_wick / candle_range
                body_ratio = candle_body / candle_range
                
                if upper_wick_ratio > 0.35:
                    trap_risk = True
                    score -= 20
                    candle_strength = "Satış Baskılı (Üst Fitil Tuzağı)"
                    details.append("⚠️ Dikkat: Uzun üst fitil (Satış Baskısı / Boğa Tuzağı Riski).")
                elif upper_wick_ratio <= 0.18 and body_ratio >= 0.65:
                    score += 15
                    candle_strength = "Güçlü Boğa (Marubozu)"
                    details.append("💪 Güçlü Boğa Mumu (Alıcılar Hakim).")

            # ==========================================
            # 3. 🎯 ORB (Opening Range Breakout - Açılış Zirvesi Kırılımı)
            # ==========================================
            orb_breakout = False
            if len(high) >= 6:
                morning_range_high = float(high.iloc[-6:-1].max())
                if current_price >= morning_range_high and vol_multiplier >= 1.4:
                    orb_breakout = True
                    score += 15
                    details.append("🎯 ORB Kırılımı: Sabah açılış bandı tepe seviyesi hacimle yukarı kırıldı!")

            # ==========================================
            # 4. OBV (Yeni Zirve & Para Girişi) (15 Puan)
            # ==========================================
            delta_price = close.diff()
            direction = np.where(delta_price > 0, 1, np.where(delta_price < 0, -1, 0))
            obv = (direction * volume).cumsum()
            current_obv = float(obv.iloc[-1])
            max_obv_20 = float(obv.iloc[-21:-1].max()) if len(obv) > 20 else float(obv.iloc[:-1].max())
            
            if current_obv >= max_obv_20:
                score += 15
                details.append("OBV yeni zirvede (Kurumsal Para Girişi).")
                
            # ==========================================
            # 5. ⚖️ KESİN VWAP ŞARTI (Mal Dağıtımı / Tuzak Filtresi)
            # ==========================================
            typical_price = (high + low + close) / 3
            if hasattr(df.index, 'date'):
                vwap = (typical_price * volume).groupby(df.index.date).cumsum() / volume.groupby(df.index.date).cumsum()
            else:
                vwap = (typical_price * volume).cumsum() / volume.cumsum()
                
            current_vwap = float(vwap.iloc[-1])
            if current_price >= current_vwap:
                score += 15
                details.append("VWAP üzerinde (Kurumsal Alım Güvenli Bölge).")
            else:
                trap_risk = True
                score -= 25
                details.append("🛑 UYARI: Fiyat VWAP altında (Mal Dağıtım Tuzağı Riski!).")
                
            # ==========================================
            # 6. EMA50 > EMA200 (Günlük Trend) (10 Puan)
            # ==========================================
            if daily_stats:
                e50 = daily_stats.get("Daily_EMA50", float('inf'))
                e200 = daily_stats.get("Daily_EMA200", float('inf'))
                if current_price > e50 and e50 > e200:
                    score += 10
                    details.append("EMA50 > EMA200 (Pozitif Trend).")
                    
            # ==========================================
            # 7. Direnç Kırılımı (10 Puan)
            # ==========================================
            highest_close_20 = float(close.iloc[-21:-1].max()) if len(close) > 20 else float(close.iloc[:-1].max())
            if current_price > highest_close_20:
                score += 10
                details.append("Direnç hacimli kırıldı.")
                
            # ==========================================
            # 8. MFI & CMF (Para Girişi & Akışı Teyidi)
            # ==========================================
            raw_money_flow = typical_price * volume
            dir_mf = np.where(typical_price > typical_price.shift(1), 1, np.where(typical_price < typical_price.shift(1), -1, 0))
            pos_flow = pd.Series(np.where(dir_mf == 1, raw_money_flow, 0), index=df.index)
            neg_flow = pd.Series(np.where(dir_mf == -1, raw_money_flow, 0), index=df.index)
            pos_mf = pos_flow.rolling(14).sum()
            neg_mf = neg_flow.rolling(14).sum()
            mfi = 100 - (100 / (1 + (pos_mf / neg_mf.replace(0, np.nan))))
            current_mfi = float(mfi.iloc[-1])
            if current_mfi > 60:
                score += 5
                
            mfv = ((close - low) - (high - close)) / (high - low).replace(0, np.nan) * volume
            cmf = mfv.rolling(20).sum() / volume.rolling(20).sum()
            current_cmf = float(cmf.iloc[-1])
            if current_cmf > 0.08:
                score += 8
                details.append("CMF Pozitif (Net Para Girişi Teyitli).")
            elif current_cmf < -0.05:
                trap_risk = True
                score -= 15
                details.append("⚠️ CMF Negatif (Yükselişte Para Çıkışı / Dağıtım Riski).")
                
            # ==========================================
            # 8. RSI & MACD (10 Puan Toplam)
            # ==========================================
            delta = close.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss.replace(0, np.nan)
            rsi = 100 - (100 / (1 + rs))
            current_rsi = float(rsi.iloc[-1])
            if 55 < current_rsi < 85:
                score += 5
                
            ema12 = close.ewm(span=12, adjust=False).mean()
            ema26 = close.ewm(span=26, adjust=False).mean()
            macd = ema12 - ema26
            macd_signal = macd.ewm(span=9, adjust=False).mean()
            if float(macd.iloc[-1]) > float(macd_signal.iloc[-1]):
                score += 5
                
            # ATR Volatilite Patlaması
            tr1 = high - low
            tr2 = (high - close.shift(1)).abs()
            tr3 = (low - close.shift(1)).abs()
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr = tr.rolling(14).mean()
            current_tr = float(tr.iloc[-1])
            prev_atr = float(atr.iloc[-2]) if len(atr) > 1 else 0
            
            if prev_atr > 0 and current_tr > prev_atr * 1.5:
                score += 5
                details.append("ATR volatilite artışı.")
                
            # ==========================================
            # 9. Tavan Evresi (Phase Sınıflandırması)
            # ==========================================
            if change_pct >= 8.0 or distance_to_ceiling_pct <= 1.8:
                phase_name = "Kilitleme Baskısı (Phase 3)"
                phase_badge = "KİLİTLEME"
                phase_color = "red"
            elif change_pct >= 4.5:
                phase_name = "İvmelenme (Phase 2)"
                phase_badge = "İVMELENME"
                phase_color = "yellow"
            else:
                phase_name = "Erken Kopuş (Phase 1)"
                phase_badge = "ERKEN KOPUŞ"
                phase_color = "green"

            # ==========================================
            # 10. ⚡ V-Dönüş / Dipten Tavan Koşusu Tespiti
            # ==========================================
            recent_lows = df[low_col].iloc[-8:] if len(df) >= 8 else df[low_col]
            session_min_low = float(recent_lows.min())
            dip_pct = ((session_min_low - prev_close) / prev_close) * 100 if prev_close > 0 else 0
            v_reversal = False
            v_power = 0.0
            if dip_pct <= -1.0 and change_pct >= 3.5:
                v_reversal = True
                v_power = round(change_pct - dip_pct, 1)
                score += 8
                details.append(f"⚡ V-Dönüş: Dip seviyeden (%{dip_pct:.1f}) +%{v_power:.1f} güçlü sıçrama!")

            # ==========================================
            # 11. ⏱️ Tahmini Tavan Kilitleme Saati (ETA)
            # ==========================================
            last_c = float(close.iloc[-1])
            prev_c = float(close.iloc[-2]) if len(close) > 1 else last_c * 0.99
            hourly_speed = max(0.4, ((last_c - prev_c) / prev_c) * 100)
            hours_needed = distance_to_ceiling_pct / hourly_speed
            now = datetime.now()
            eta_time = now + timedelta(hours=min(4.0, max(0.5, hours_needed)))
            if eta_time.hour >= 18:
                eta_str = "Seans Kapanışı (17:45-18:00)"
            else:
                eta_end = eta_time + timedelta(minutes=25)
                eta_str = f"{eta_time.strftime('%H:%M')} - {eta_end.strftime('%H:%M')}"

            # ==========================================
            # 12. 🚨 Tavan Çözülme / Satış Baskısı Koruması
            # ==========================================
            breakdown_risk = False
            breakdown_warning = None
            if distance_to_ceiling_pct <= 2.2 or change_pct >= 7.8:
                if trap_risk or (current_rsi > 78 and len(rsi) > 1 and float(rsi.iloc[-1]) < float(rsi.iloc[-2])):
                    breakdown_risk = True
                    breakdown_warning = "Tavanda Satış Baskısı / Çözülme Riski! Kâr Al veya Stopu Sıkılaştır."
                    details.append(f"🚨 {breakdown_warning}")

            # ==========================================
            # 13. ♟️ Domino Etkisi & Sektörel Kardeş Hisseler
            # ==========================================
            clean_sym = symbol.replace(".IS", "")
            domino_sector = None
            domino_peers = []
            try:
                from config.bist_symbols import DOMINO_CLUSTERS, WARRANT_UNDERLYING_MAP
                for sec_name, sec_syms in DOMINO_CLUSTERS.items():
                    if symbol in sec_syms or f"{clean_sym}.IS" in sec_syms:
                        domino_sector = sec_name
                        domino_peers = [s.replace(".IS", "") for s in sec_syms if s.replace(".IS", "") != clean_sym]
                        break
            except Exception:
                WARRANT_UNDERLYING_MAP = {}

            if domino_sector and domino_peers:
                peer_sample = ", ".join(domino_peers[:3])
                details.append(f"♟️ Domino Grubu ({domino_sector}): Peşinden gelebilecek kardeş hisseler: #{peer_sample}")

            # ==========================================
            # 14. 🎯 Varant Kaldıraç Eşleştirmesi
            # ==========================================
            warrant_match = None
            try:
                warrant_info = WARRANT_UNDERLYING_MAP.get(clean_sym)
                if warrant_info:
                    warrant_lev = warrant_info.get("leverage", 6.0)
                    expected_warrant_gain = round(distance_to_ceiling_pct * warrant_lev, 1)
                    warrant_match = {
                        "Prefix": warrant_info.get("prefix"),
                        "Name": warrant_info.get("name"),
                        "Leverage": f"{warrant_lev}x",
                        "Potential_Gain_Pct": expected_warrant_gain,
                        "Desc": f"Spot +%{distance_to_ceiling_pct:.1f} tavana ulaşırsa varant potansiyeli: +%{expected_warrant_gain:.0f}"
                    }
            except Exception:
                warrant_match = None

            # ==========================================
            # 15. 🔗 Tavan Zinciri & Seri Potansiyeli (Çift Tavan Skoru)
            # ==========================================
            streak_score = min(96, max(45, int(score * 0.92 + (10 if vol_multiplier >= 2.0 else 0) + (5 if v_reversal else 0))))
            streak_potential = f"%{streak_score} (Çift Tavan İhtimali)"
                
            # ==========================================
            # 16. Pozisyon Algoritması (Dinamik İz Süren Stop & Hedefler)
            # ==========================================
            sl_vwap = current_vwap * 0.992 # VWAP altı %0.8 tolerans
            sl_fixed = current_price * 0.975 # %2.5 sabit stop
            sl = max(sl_vwap, sl_fixed)
            if sl >= current_price:
                sl = current_price * 0.98
            
            tp1 = round(highest_close_20 * 1.015, 2)
            if tp1 <= current_price:
                tp1 = round(current_price * 1.03, 2)
                
            tp2 = round(tavan_price, 2)
            if tp2 <= tp1:
                tp2 = round(current_price * 1.095, 2)
                
            risk_unit = max(0.01, current_price - sl)
            reward_unit = max(0.01, tp2 - current_price)
            rr_ratio = round(reward_unit / risk_unit, 2)
                
            position = {
                "Entry": round(current_price, 2),
                "SL": round(sl, 2),
                "TP1": round(tp1, 2),
                "TP2": round(tp2, 2),
                "RR": rr_ratio,
                "Projection": eta_str
            }
                
        except Exception as e:
            print(f"[TavanAdayi] Hesaplama hatasi: {e}")
            return None
            
        if score < 50:
            return None
            
        score = min(100, max(0, score))
        report = " ".join(details)

        # 🛡️ Anti-Trap Shield & Teyit Skoru Hesaplama
        if not trap_risk and current_price >= current_vwap and vol_multiplier >= 1.4:
            anti_trap_badge = "🛡️ TEYİTLİ TAVAN"
            anti_trap_color = "#10b981"
            teyit_score = min(99, max(75, int(score * 0.95 + (8 if orb_breakout else 0) + (5 if current_cmf > 0.08 else 0))))
        elif trap_risk or current_price < current_vwap:
            anti_trap_badge = "⚠️ TUZAK / FİTİL RİSKİ"
            anti_trap_color = "#ef4444"
            teyit_score = max(25, int(score * 0.55))
        else:
            anti_trap_badge = "🟡 GÖZLEM / NÖTR"
            anti_trap_color = "#facc15"
            teyit_score = max(50, int(score * 0.75))
            
        # ==========================================
        # 🧪 AR-GE: SAF MADDE (ZENGİNLEŞTİRİLMİŞ ARITMA)
        # ==========================================
        # 1. Bollinger Daralması (Fiyat Sıkışması)
        roll_mean = close.rolling(20).mean()
        roll_std = close.rolling(20).std(ddof=0)
        upper_band = roll_mean + (roll_std * 2)
        lower_band = roll_mean - (roll_std * 2)
        
        current_upper = float(upper_band.iloc[-1])
        current_lower = float(lower_band.iloc[-1])
        current_mid = float(roll_mean.iloc[-1])
        
        squeeze_pct = ((current_upper - current_lower) / current_mid) * 100 if current_mid > 0 else 0
        
        # 2. Patlama Olasılığı (P-Score)
        rsi_weight = 0
        if 55 < current_rsi < 75: rsi_weight = 35
        elif current_rsi >= 75: rsi_weight = 15  # Aşırı alım
        elif current_rsi > 40: rsi_weight = 10
        
        # Squeeze Pct ne kadar düşükse, bantlar o kadar dardır (Patlama ihtimali yüksek)
        # Squeeze 2.0% (Dar) -> 40 Puan | Squeeze 10.0% (Geniş) -> 0 Puan
        sqz_weight = max(0, 40 - (squeeze_pct * 4)) 
        
        # Hacim çarpanı 3x ise 25 puan, 1x ise 8 puan
        vol_weight = min(25, vol_multiplier * 8)
        
        p_score = int(rsi_weight + sqz_weight + vol_weight)
        p_score = min(99, max(1, p_score))
        
        # 3. Kurumsal Ayak İzi (Tahtacı Akümülasyon/Dağıtım)
        candle_range_hf = current_high - current_low
        if candle_range_hf > 0:
            close_position = (current_price - current_low) / candle_range_hf
            if close_position > 0.7 and vol_multiplier >= 1.2:
                footprint = "Toplama (Akümülasyon)"
                footprint_color = "green"
            elif close_position < 0.35 and vol_multiplier >= 1.2:
                footprint = "Dağıtım (Tuzak)"
                footprint_color = "red"
            else:
                footprint = "Nötr (Bekleme)"
                footprint_color = "yellow"
        else:
            footprint = "Nötr (Bekleme)"
            footprint_color = "yellow"
            
        # 4. Kısa Vade İvme (Momentum Hızlanması)
        momentum_accel = False
        if len(close) >= 3:
            change_1 = float(close.iloc[-1]) - float(close.iloc[-2])
            change_2 = float(close.iloc[-2]) - float(close.iloc[-3])
            if change_1 > change_2 and change_1 > 0 and change_2 > 0:
                momentum_accel = True
        
        # ==========================================
        # 👑 AR-GE EKSTRALAR (Faz 3)
        # ==========================================
        # 1. Alpha Gücü (Göreceli BIST Ayrışması Proxy)
        # EMA21'den sapma * hacim şiddeti * CMF
        ema21 = close.ewm(span=21, adjust=False).mean()
        c_ema21 = float(ema21.iloc[-1])
        alpha_val = ((current_price - c_ema21) / c_ema21) * 100 * vol_multiplier
        if alpha_val > 15:
            alpha_str = f"Pozitif (+%{round(alpha_val,1)})"
        elif alpha_val < 0:
            alpha_str = f"Negatif (%{round(alpha_val,1)})"
        else:
            alpha_str = f"Nötr (+%{round(alpha_val,1)})"

        # 2. Şort Sıkıştırması (Squeeze Riski)
        # ADX Hesaplama
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
        current_adx = float(adx.iloc[-1])
        
        short_squeeze = "Yok"
        if current_adx > 30 and current_rsi > 70 and squeeze_pct < 4.0:
            short_squeeze = "🔥 Patlatma Yakın"
        elif current_adx > 25 and current_rsi > 65:
            short_squeeze = "Yükseliyor"
            
        # 3. Akıllı Para (Smart Money CMF)
        smart_money = "Nötr Para"
        if current_cmf > 0.15:
            smart_money = "🟢 Güçlü Giriş"
        elif current_cmf > 0.05:
            smart_money = "🟢 Akümülasyon"
        elif current_cmf < -0.1:
            smart_money = "🔴 Sert Çıkış"
        elif current_cmf < 0:
            smart_money = "🔴 Dağıtım"
            
        # 4. Domino Etkisi
        domino_str = "Yok"
        if domino_peers and len(domino_peers) > 0:
            domino_str = f"#{', #'.join(domino_peers[:2])}"
            
        
        return {
            "Symbol": symbol,
            "Price": round(current_price, 2),
            "Daily_Change_Pct": round(change_pct, 2),
            "Ceiling_Price": round(tavan_price, 2),
            "Distance_To_Ceiling_Pct": round(distance_to_ceiling_pct, 2),
            "Phase": phase_name,
            "Phase_Badge": phase_badge,
            "Phase_Color": phase_color,
            "Vol_Multiplier": vol_multiplier,
            "Candle_Strength": candle_strength,
            "Trap_Risk": trap_risk,
            "Anti_Trap_Badge": anti_trap_badge,
            "Anti_Trap_Color": anti_trap_color,
            "Teyit_Score": teyit_score,
            "ORB_Breakout": orb_breakout,
            "VWAP": round(current_vwap, 2),
            "V_Reversal": v_reversal,
            "V_Power": round(v_power, 1),
            "ETA": eta_str,
            "Breakdown_Risk": breakdown_risk,
            "Breakdown_Warning": breakdown_warning,
            "Domino_Sector": domino_sector,
            "Domino_Peers": domino_peers,
            "Domino_Str": domino_str,
            "Warrant_Match": warrant_match,
            "Streak_Score": streak_score,
            "Streak_Potential": streak_potential,
            "Squeeze_Pct": round(squeeze_pct, 2),
            "P_Score": p_score,
            "Footprint": footprint,
            "Footprint_Color": footprint_color,
            "Momentum_Accel": momentum_accel,
            "Alpha_Str": alpha_str,
            "Alpha_Val": round(alpha_val, 2),
            "Short_Squeeze": short_squeeze,
            "Smart_Money": smart_money,
            "Score": score,
            "Report": report,
            "Position": position
        }

    def analyze_5m_rsi_strategy(self, symbol: str, data: Any = None) -> Dict[str, Any]:
        """
        5 Dakikalık Kısa Trade RSI Stratejisi
        RSI 50'yi yukarı keserse AL, 70'i aşağı keserse SAT sinyali üretir.
        """
        if data is None or not isinstance(data, pd.DataFrame) or data.empty or len(data) < 20:
            return None
            
        df = data.copy()
        
        # Standardize columns
        close_col = 'close' if 'close' in df.columns else 'Close'
        if close_col not in df.columns:
            return None
            
        close = df[close_col]
        current_price = float(close.iloc[-1])
        
        try:
            # RSI (14) Hesaplama
            delta = close.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss.replace(0, float('nan'))
            rsi = 100 - (100 / (1 + rs))
            
            # Son 3 barı alalım (Kesişimi kontrol etmek için)
            # -1: Güncel Bar, -2: Bir Önceki Bar
            if len(rsi) < 3 or pd.isna(rsi.iloc[-1]) or pd.isna(rsi.iloc[-2]):
                return None
                
            rsi_current = float(rsi.iloc[-1])
            rsi_prev = float(rsi.iloc[-2])
            
            signal = None
            
            # AL Sinyali: RSI 50'yi aşağıdan yukarı kesiyor
            if rsi_prev < 50 and rsi_current >= 50:
                signal = "AL"
                
            # SAT Sinyali: RSI 70'i yukarıdan aşağı kesiyor
            elif rsi_prev > 70 and rsi_current <= 70:
                signal = "SAT"
                
            if signal:
                # Zamani da alalım
                time_str = ""
                if hasattr(df.index, 'strftime'):
                    time_str = df.index[-1].strftime("%H:%M")
                
                return {
                    "Symbol": symbol,
                    "Price": round(current_price, 2),
                    "RSI": round(rsi_current, 2),
                    "Signal": signal,
                    "Time": time_str
                }
                
        except Exception as e:
            print(f"[5m RSI] Hesaplama hatasi ({symbol}): {e}")
            return None
            
        return None


    def analyze_1h_stay_away(self, symbol: str, data: Any = None) -> Dict[str, Any]:
        """
        1 Saatlik (1h) veriler üzerinde UZAK DUR (Stay Away / Negatif Momentum) analizi yapar.
        analyze_1h_opportunities metodunun tam tersidir.
        """
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

    def check_custom_strict_strategy(self, df, direction: str = "AL", lookback_bars: int = 50):
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
            return False, 0, ""
                
    def check_ema_stop_loss(self, df, interval="1h"):
        """Checks for EMA 9 crossing below EMA 21 to trigger a stop loss"""
        if df.empty or len(df) < 30:
            return False, ""
        try:
            import pandas as pd
            import numpy as np
            
            close_col = 'close' if 'close' in df.columns else 'Close'
            vol_col = 'volume' if 'volume' in df.columns else 'Volume'
            
            close = df[close_col]
            vol = df[vol_col]
            
            ema9 = close.ewm(span=9, adjust=False).mean()
            ema21 = close.ewm(span=21, adjust=False).mean()
            
            c_ema9, c_ema21 = float(ema9.iloc[-1]), float(ema21.iloc[-1])
            p_ema9, p_ema21 = float(ema9.iloc[-2]), float(ema21.iloc[-2])
            
            crossed_down = (p_ema9 >= p_ema21) and (c_ema9 < c_ema21)
            
            if interval == "1h":
                if crossed_down or (c_ema9 < c_ema21):
                    return True, "1H EMA 9 Altında"
            elif interval == "15m":
                vol_sma = vol.rolling(20).mean()
                c_vol, avg_vol = float(vol.iloc[-1]), float(vol_sma.iloc[-1])
                if crossed_down and c_vol > avg_vol * 1.5:
                    return True, "15M Hacimli Kesişim"
            return False, ""
        except Exception:
            return False, ""
        except Exception as e:
            return False, 0, ""