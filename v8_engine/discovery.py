import pandas as pd
import numpy as np

class DiscoveryEngine:
    """
    V8 Discovery Engine - Hareket Öncesi Radar
    Hisse henüz sert yükselmeden, taban oluşumu, sıkışma ve hacim hazırlığını yakalar.
    Çoklu zaman penceresinde (Kısa 5b, Orta 20b, Uzun 50b) konsensus skoru üretir.
    """
    STATE_TR_MAP = {
        "READY": "HAZIR (KIRILIM YAKIN)",
        "PREPARING": "SIKIŞMA (HAZIRLIK)",
        "WATCH": "İZLEMEDE",
        "NONE": "NÖTR",
        "ERROR": "BİLGİ ALINAMADI"
    }

    def __init__(self):
        pass
        
    def analyze_preparation(self, df: pd.DataFrame, symbol: str) -> dict:
        """
        Gelen DataFrame üzerinde volatilite, hacim ve momentum sıkışmasını analiz eder.
        """
        if df is None or len(df) < 15:
            return self._default_result(symbol, "DATA_INSUFFICIENT")
            
        try:
            close = df['Close'] if 'Close' in df.columns else df['close']
            high = df['High'] if 'High' in df.columns else df['high']
            low = df['Low'] if 'Low' in df.columns else df['low']
            vol = df['Volume'] if 'Volume' in df.columns else df['volume']
            
            if vol.sum() == 0 or len(close) < 10:
                return self._default_result(symbol, "NO_VOLUME")
            
            # --- 1. TÜM SERİ ÜZERİNDE GÖSTERGELER (NaN oluşumunu engeller) ---
            rolling_mean = close.rolling(20, min_periods=5).mean()
            rolling_std = close.rolling(20, min_periods=5).std().fillna(0)
            upper_band = rolling_mean + (rolling_std * 2)
            lower_band = rolling_mean - (rolling_std * 2)
            bb_width = ((upper_band - lower_band) / rolling_mean.replace(0, np.nan)) * 100
            bb_width = bb_width.fillna(5.0)

            tr1 = high - low
            tr2 = abs(high - close.shift())
            tr3 = abs(low - close.shift())
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr = tr.rolling(14, min_periods=5).mean()
            atr_pct = ((atr / close.replace(0, np.nan)) * 100).fillna(2.0)

            vol_sma = vol.rolling(10, min_periods=3).mean().replace(0, np.nan)
            rel_vol = vol / vol_sma
            rel_vol = rel_vol.fillna(1.0)

            ema20 = close.ewm(span=20, min_periods=5).mean()
            dist_ema20 = ((close - ema20) / ema20.replace(0, np.nan)) * 100
            dist_ema20 = dist_ema20.fillna(0.0)

            # --- 2. ÇOKLU ZAMAN PENCERESİ SKORLAMASI ---
            # Kısa (5 bar), Orta (20 bar), Uzun (50 bar)
            tf_scores = {}
            for tf_label, lookback in [("short", 5), ("medium", 20), ("long", 50)]:
                eff_lb = min(len(close), lookback)
                sub_close = close.iloc[-eff_lb:]
                sub_high = high.iloc[-eff_lb:]
                sub_low = low.iloc[-eff_lb:]
                sub_vol = vol.iloc[-eff_lb:]
                sub_rel_vol = rel_vol.iloc[-eff_lb:]
                sub_bb = bb_width.iloc[-eff_lb:]
                sub_atr = atr_pct.iloc[-eff_lb:]
                sub_dist = dist_ema20.iloc[-eff_lb:]

                # A) Sıkışma Skoru (0-40)
                comp_score = 0.0
                cur_bb = float(sub_bb.iloc[-1])
                avg_bb = float(sub_bb.mean()) if len(sub_bb) > 0 else cur_bb
                if avg_bb > 0 and cur_bb < avg_bb * 0.85:
                    comp_score += 20.0
                if avg_bb > 0 and cur_bb < avg_bb * 0.60:
                    comp_score += 10.0
                
                cur_atr = float(sub_atr.iloc[-1])
                avg_atr = float(sub_atr.mean()) if len(sub_atr) > 0 else cur_atr
                if avg_atr > 0 and cur_atr < avg_atr * 0.90:
                    comp_score += 10.0

                # B) Hacim Birikimi Skoru (0-35)
                vol_score = 0.0
                cur_rvol = float(sub_rel_vol.iloc[-1])
                prev_rvol = float(sub_rel_vol.iloc[-2]) if len(sub_rel_vol) > 1 else cur_rvol
                if cur_rvol >= 1.5:
                    vol_score += 20.0
                elif cur_rvol >= 1.1:
                    vol_score += 12.0
                
                if cur_rvol > prev_rvol and float(sub_close.iloc[-1]) >= float(sub_close.iloc[-2]):
                    vol_score += 15.0 # Hacimli yükselen gün

                # C) Yapı / Taban Skoru (0-25)
                struct_score = 0.0
                h_max = float(sub_high.max())
                l_min = float(sub_low.min())
                range_pct = ((h_max - l_min) / l_min) * 100 if l_min > 0 else 100
                if range_pct < 6.0:
                    struct_score += 15.0 # Çok dar konsolidasyon bandı
                elif range_pct < 10.0:
                    struct_score += 8.0

                cur_dist = float(sub_dist.iloc[-1])
                if -1.5 <= cur_dist <= 3.0:
                    struct_score += 10.0 # EMA20 üzerinde sağlıklı tutunma

                total_window = min(100.0, comp_score + vol_score + struct_score)
                tf_scores[tf_label] = {
                    "total": round(total_window, 1),
                    "compression": round(comp_score, 1),
                    "volume": round(vol_score, 1),
                    "structure": round(struct_score, 1)
                }

            # Konsensus: Kısa %45, Orta %35, Uzun %20
            weights = {"short": 0.45, "medium": 0.35, "long": 0.20}
            total_score = sum(tf_scores[tf]["total"] * weights.get(tf, 0) for tf in tf_scores)
            avg_compression = np.mean([tf_scores[tf]["compression"] for tf in tf_scores])
            avg_volume = np.mean([tf_scores[tf]["volume"] for tf in tf_scores])
            avg_structure = np.mean([tf_scores[tf]["structure"] for tf in tf_scores])

            # STATE Belirleme & Türkçe Gerekçeler
            state = "NONE"
            reasons = []

            if total_score >= 62:
                state = "READY"
                if avg_compression >= 15:
                    reasons.append("Çoklu periyotta volatilite daralması")
                if avg_volume >= 15:
                    reasons.append("Kademeli hacim birikimi ve para girişi")
                if avg_structure >= 10:
                    reasons.append("Dar bant konsolidasyonu & EMA desteği")
                if not reasons:
                    reasons.append("Tüm zaman pencerelerinde kırılım hazırlığı tamamlandı")
            elif total_score >= 42:
                state = "PREPARING"
                if avg_compression >= 10:
                    reasons.append("Volatilite daralıyor, patlama yakın")
                if avg_volume >= 10:
                    reasons.append("Göreceli hacim artış trendinde")
                if not reasons:
                    reasons.append("Taban oluşumu ve sıkışma devam ediyor")
            elif total_score >= 20:
                state = "WATCH"
                reasons.append("Hissede izleme seviyesinde konsolidasyon mevcut")

            latest_bb = round(float(bb_width.iloc[-1]), 2)
            latest_atr = round(float(atr_pct.iloc[-1]), 2)
            latest_rvol = round(float(rel_vol.iloc[-1]), 2)
            latest_dist = round(float(dist_ema20.iloc[-1]), 2)

            state_tr = self.STATE_TR_MAP.get(state, "İZLEMEDE")
            return {
                "symbol": symbol,
                "preparation_score": round(total_score, 1),
                "state": state_tr,
                "state_code": state,
                "state_label": state_tr,
                "reasons": reasons,
                "timeframe_breakdown": tf_scores,
                "metrics": {
                    "bb_width_pct": latest_bb,
                    "atr_pct": latest_atr,
                    "relative_volume": latest_rvol,
                    "dist_ema20": latest_dist
                }
            }
            
        except Exception as e:
            print(f"[V8 Discovery Engine] {symbol} error: {e}")
            return self._default_result(symbol, "ERROR")

    def _default_result(self, symbol, state):
        state_tr = self.STATE_TR_MAP.get(state, "İZLEMEDE")
        return {
            "symbol": symbol,
            "preparation_score": 0.0,
            "state": state_tr,
            "state_code": state,
            "state_label": state_tr,
            "reasons": ["Yetersiz veri veya hesaplama yapılamadı"],
            "timeframe_breakdown": {},
            "metrics": {
                "bb_width_pct": 0.0,
                "atr_pct": 0.0,
                "relative_volume": 1.0,
                "dist_ema20": 0.0
            }
        }
