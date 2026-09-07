import pandas as pd
import numpy as np

class DiscoveryEngine:
    """
    V8 Discovery Engine - Hareket Öncesi Radar
    Hisse henüz sert yükselmeden, sıkışma ve hacim hazırlığını yakalar.
    Artık çoklu zaman penceresinde (5, 20, 50 bar) ve farklı hızlandırılmış
    periyotlarla (Kısa/Orta/Uzun) konsensus skoru üretir.
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
            
            # --- ÇOKLU ZAMAN PENCERESİ KONSENSUSU ---
            tf_scores = {}
            for tf_label, lookback in [("short", 5), ("medium", 20), ("long", 50)]:
                if len(close) < lookback + 5:
                    continue
                sub_close = close.iloc[-lookback:]
                sub_high = high.iloc[-lookback:]
                sub_low = low.iloc[-lookback:]
                sub_vol = vol.iloc[-lookback:]
                tf_scores[tf_label] = self._score_window(sub_close, sub_high, sub_low, sub_vol)
            
            if not tf_scores:
                return self._default_result(symbol, "DATA_INSUFFICIENT")
            
            # Konsensus: kısa %40, orta %35, uzun %25
            weights = {"short": 0.40, "medium": 0.35, "long": 0.25}
            total_score = sum(tf_scores[tf]["total"] * weights.get(tf, 0) for tf in tf_scores)
            avg_compression = np.mean([tf_scores[tf]["compression"] for tf in tf_scores])
            avg_volume = np.mean([tf_scores[tf]["volume"] for tf in tf_scores])
            avg_structure = np.mean([tf_scores[tf]["structure"] for tf in tf_scores])
            
            # Son periyot özel metrikler (UI için)
            latest_metrics = self._score_window(close, high, low, vol)
            
            # STATE belirleme
            state = "NONE"
            reasons = []
            
            # Çoklu timeframe uyuşması
            aligned_ready = sum(1 for tf in tf_scores if tf_scores[tf]["total"] >= 70)
            aligned_preparing = sum(1 for tf in tf_scores if tf_scores[tf]["total"] >= 50)
            
            if total_score >= 75 and aligned_ready >= 2:
                state = "READY"
                if avg_compression >= 25: reasons.append("Multi-Timeframe Compression")
                if avg_volume >= 20: reasons.append("Cross-Timeframe Volume Build")
                if avg_structure >= 12: reasons.append("Tight Range & EMA Alignment")
            elif total_score >= 55 and aligned_preparing >= 2:
                state = "PREPARING"
                if avg_compression >= 15: reasons.append("Volatility is dropping")
                if avg_volume >= 15: reasons.append("Relative volume rising")
            elif total_score >= 35:
                state = "WATCH"
            
            return {
                "symbol": symbol,
                "preparation_score": round(total_score, 1),
                "state": state,
                "reasons": reasons,
                "timeframe_breakdown": {
                    tf: {
                        "score": round(tf_scores[tf]["total"], 1),
                        "compression": round(tf_scores[tf]["compression"], 1),
                        "volume": round(tf_scores[tf]["volume"], 1),
                        "structure": round(tf_scores[tf]["structure"], 1),
                    } for tf in tf_scores
                },
                "metrics": {
                    "bb_width_pct": round(latest_metrics["bb_width"], 2),
                    "atr_pct": round(latest_metrics["atr_pct"], 2),
                    "relative_volume": round(latest_metrics["rel_vol"], 2),
                    "dist_ema20": round(latest_metrics["dist_ema20"], 2),
                    "timeframe_alignment": aligned_ready
                }
            }
            
        except Exception as e:
            print(f"[V8 Discovery Engine] {symbol} error: {e}")
            return self._default_result(symbol, "ERROR")
    
    def _score_window(self, close, high, low, vol) -> dict:
        """Belirli bir pencere için compression/volume/structure skorları döndürür."""
        try:
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
                compression_score += 15
            if np.isnan(compression_score):
                compression_score = 0
                
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
                compression_score += 15
                
            # Hacim
            vol_sma = vol.rolling(10).mean()
            current_vol = float(vol.iloc[-1])
            prev_vol = float(vol.iloc[-2]) if len(vol) > 1 else current_vol
            avg_vol = float(vol_sma.iloc[-1])
            prev_avg_vol = float(vol_sma.iloc[-2]) if len(vol_sma) > 1 else avg_vol
            
            rel_vol = current_vol / avg_vol if avg_vol > 0 else 1
            prev_rel_vol = prev_vol / prev_avg_vol if prev_avg_vol > 0 else 1
            
            volume_score = 0
            if rel_vol > 1.2:
                volume_score += 15
            if rel_vol > 1.5:
                volume_score += 10
            if rel_vol > prev_rel_vol and float(close.iloc[-1]) > float(close.iloc[-2]):
                volume_score += 15
                
            # Yapı
            recent_max = float(high.rolling(5).max().iloc[-1])
            recent_min = float(low.rolling(5).min().iloc[-1])
            range_pct = ((recent_max - recent_min) / recent_min) * 100 if recent_min > 0 else 100
            
            structure_score = 0
            if range_pct < 4.0:
                structure_score += 10
                
            ema20 = close.ewm(span=20).mean()
            c_ema20 = float(ema20.iloc[-1])
            dist_ema20 = ((float(close.iloc[-1]) - c_ema20) / c_ema20) * 100 if c_ema20 != 0 else 0
            if -1.0 <= dist_ema20 <= 2.0:
                structure_score += 10
            
            total = min(100.0, float(compression_score + volume_score + structure_score))
            
            return {
                "total": total,
                "compression": compression_score,
                "volume": volume_score,
                "structure": structure_score,
                "bb_width": current_bb_width,
                "atr_pct": current_atr_pct,
                "rel_vol": rel_vol,
                "dist_ema20": dist_ema20,
            }
        except Exception as e:
            print(f"[V8 Discovery Engine] _score_window error: {e}")
            return {
                "total": 0, "compression": 0, "volume": 0, "structure": 0,
                "bb_width": 0, "atr_pct": 0, "rel_vol": 1, "dist_ema20": 0,
            }
            
    def _default_result(self, symbol, state):
        return {
            "symbol": symbol,
            "preparation_score": 0.0,
            "state": state,
            "reasons": [],
            "timeframe_breakdown": {},
            "metrics": {}
        }
