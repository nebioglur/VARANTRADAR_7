import pandas as pd
import numpy as np

class DiscoveryEngine:
    """
    V8 Discovery Engine - Hareket Öncesi Radar
    Hisse henüz sert yükselmeden, sıkışma ve hacim hazırlığını yakalar.
    Amacı fırsatları patlamadan hemen önce "READY" veya "PREPARING" olarak işaretlemektir.
    """
    def __init__(self):
        pass
        
    def analyze_preparation(self, df: pd.DataFrame, symbol: str) -> dict:
        """
        Gelen DataFrame üzerinde volatilite, hacim ve momentum sıkışmasını analiz eder.
        """
        if df is None or len(df) < 30:
            return self._default_result(symbol, "DATA_INSUFFICIENT")
            
        try:
            close = df['Close'] if 'Close' in df.columns else df['close']
            high = df['High'] if 'High' in df.columns else df['high']
            low = df['Low'] if 'Low' in df.columns else df['low']
            vol = df['Volume'] if 'Volume' in df.columns else df['volume']
            
            if vol.sum() == 0:
                return self._default_result(symbol, "NO_VOLUME")
                
            # --- 1. VOLATİLİTE SIKIŞMASI (Compression) ---
            # Bollinger Bands
            rolling_mean = close.rolling(20).mean()
            rolling_std = close.rolling(20).std()
            upper_band = rolling_mean + (rolling_std * 2)
            lower_band = rolling_mean - (rolling_std * 2)
            bb_width = ((upper_band - lower_band) / rolling_mean) * 100
            
            current_bb_width = float(bb_width.iloc[-1])
            avg_bb_width = float(bb_width.rolling(20).mean().iloc[-1])
            
            compression_score = 0
            if current_bb_width < avg_bb_width * 0.8:
                compression_score += 20
            if current_bb_width < avg_bb_width * 0.5:
                compression_score += 15 # Toplam 35
                
            # ATR (Volatility)
            tr1 = high - low
            tr2 = abs(high - close.shift())
            tr3 = abs(low - close.shift())
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr = tr.rolling(14).mean()
            atr_pct = (atr / close) * 100
            
            current_atr_pct = float(atr_pct.iloc[-1])
            avg_atr_pct = float(atr_pct.rolling(20).mean().iloc[-1])
            if current_atr_pct < avg_atr_pct * 0.9:
                compression_score += 15 # Toplam 50
                
            # --- 2. HACİM HAZIRLIĞI (Volume Preparation) ---
            vol_sma_10 = vol.rolling(10).mean()
            current_vol = float(vol.iloc[-1])
            prev_vol = float(vol.iloc[-2]) if len(vol) > 1 else current_vol
            avg_vol_10 = float(vol_sma_10.iloc[-1])
            prev_avg_vol_10 = float(vol_sma_10.iloc[-2]) if len(vol_sma_10) > 1 else avg_vol_10
            
            rel_vol = current_vol / avg_vol_10 if avg_vol_10 > 0 else 1
            prev_rel_vol = prev_vol / prev_avg_vol_10 if prev_avg_vol_10 > 0 else 1
            
            volume_score = 0
            if rel_vol > 1.2:
                volume_score += 15
            if rel_vol > 1.5:
                volume_score += 10
            if rel_vol > prev_rel_vol and float(close.iloc[-1]) > float(close.iloc[-2]):
                volume_score += 15 # Hacim artıyor, fiyat destekliyor. Toplam 40
                
            # --- 3. MOMENTUM & FİYAT YAPISI (Price Structure) ---
            # Fiyat ne kadar yatay?
            recent_max = float(high.rolling(5).max().iloc[-1])
            recent_min = float(low.rolling(5).min().iloc[-1])
            range_pct = ((recent_max - recent_min) / recent_min) * 100 if recent_min > 0 else 100
            
            structure_score = 0
            if range_pct < 4.0: # Son 5 günde %4'ten az dalgalanma (Sıkışma)
                structure_score += 10
                
            # Trend Alignment
            ema20 = close.ewm(span=20).mean()
            c_ema20 = float(ema20.iloc[-1])
            
            # Fiyat 20 günlük EMA üzerinde veya çok yakın mı?
            dist_ema20 = ((float(close.iloc[-1]) - c_ema20) / c_ema20) * 100
            if -1.0 <= dist_ema20 <= 2.0:
                structure_score += 10 # Çok uzaklaşmamış, destek buluyor
                
            # TOTAL PREPARATION SCORE
            total_score = min(100.0, float(compression_score + volume_score + structure_score))
            
            # STATE belirleme
            state = "NONE"
            reasons = []
            
            if total_score >= 75:
                state = "READY"
                if compression_score >= 30: reasons.append("Bollinger/ATR Compression")
                if volume_score >= 25: reasons.append("Volume Accumulation")
                if structure_score >= 15: reasons.append("Tight Range & EMA Alignment")
            elif total_score >= 50:
                state = "PREPARING"
                if compression_score >= 20: reasons.append("Volatility is dropping")
                if volume_score >= 15: reasons.append("Relative volume rising")
            elif total_score >= 30:
                state = "WATCH"
            
            return {
                "symbol": symbol,
                "preparation_score": round(total_score, 1),
                "state": state,
                "reasons": reasons,
                "metrics": {
                    "bb_width_pct": round(current_bb_width, 2),
                    "atr_pct": round(current_atr_pct, 2),
                    "relative_volume": round(rel_vol, 2),
                    "dist_ema20": round(dist_ema20, 2)
                }
            }
            
        except Exception as e:
            print(f"[V8 Discovery Engine] {symbol} error: {e}")
            return self._default_result(symbol, "ERROR")
            
    def _default_result(self, symbol, state):
        return {
            "symbol": symbol,
            "preparation_score": 0.0,
            "state": state,
            "reasons": [],
            "metrics": {}
        }
