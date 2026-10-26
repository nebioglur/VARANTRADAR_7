import pandas as pd
import numpy as np
from typing import Dict, Any

class BreakoutEngine:
    """
    V8 Breakout & False Breakout Engine
    Kırılımları tespit eder ve kalitesini (gerçek mi tuzak mı) detaylı puanlar.
    """
    STATUS_TR_MAP = {
        "CONFIRMED_BREAKOUT": "ONAYLI KIRILIM (GÜÇLÜ)",
        "SUSPICIOUS_BREAKOUT": "ŞÜPHELİ KIRILIM (TAKİP)",
        "LIKELY_FAKEOUT": "TUZAK RİSKİ YÜKSEK",
        "NO_BREAKOUT": "KIRILIM YOK",
        "DATA_INSUFFICIENT": "VERİ YETERSİZ",
        "ERROR": "HATA"
    }

    def __init__(self):
        pass

    def analyze_breakout(self, df: pd.DataFrame, symbol: str, market_regime: str = "NEUTRAL") -> Dict[str, Any]:
        """
        Son barlardaki kırılımları analiz eder.
        """
        if df is None or len(df) < 25:
            return self._default_result(symbol, "DATA_INSUFFICIENT")

        try:
            close = df['Close'] if 'Close' in df.columns else df['close']
            high = df['High'] if 'High' in df.columns else df['high']
            low = df['Low'] if 'Low' in df.columns else df['low']
            open_p = df['Open'] if 'Open' in df.columns else df['open']
            vol = df['Volume'] if 'Volume' in df.columns else df['volume']

            if vol.sum() == 0 or len(close) < 15:
                return self._default_result(symbol, "NO_VOLUME")

            c = float(close.iloc[-1])
            prev_c = float(close.iloc[-2]) if len(close) > 1 else c
            h = float(high.iloc[-1])
            l = float(low.iloc[-1])
            o = float(open_p.iloc[-1])
            v = float(vol.iloc[-1])

            change_pct = ((c - prev_c) / prev_c) * 100 if prev_c > 0 else 0.0

            # 1. DİRENÇLERİ VE BANTLARI BELİRLE
            # 10 günlük ve 20 günlük yerel dirençler
            lb_10 = min(len(high) - 2, 10)
            lb_20 = min(len(high) - 2, 20)
            res_10d = float(high.iloc[-lb_10-1:-1].max()) if lb_10 > 2 else h
            res_20d = float(high.iloc[-lb_20-1:-1].max()) if lb_20 > 2 else h
            local_resistance = min(res_10d, res_20d)

            # Bollinger Bantları
            bb_mean = close.rolling(20, min_periods=5).mean()
            bb_std = close.rolling(20, min_periods=5).std().fillna(0)
            bb_upper = bb_mean + (bb_std * 2)
            c_bb_upper = float(bb_upper.iloc[-1]) if len(bb_upper) > 0 else c

            # Hacim Teyidi
            vol_sma_10 = vol.rolling(10, min_periods=3).mean().replace(0, np.nan)
            avg_vol = float(vol_sma_10.iloc[-1]) if len(vol_sma_10) > 0 else v
            rel_vol = v / avg_vol if avg_vol > 0 else 1.0

            # 2. KIRILIM TESPİTİ (3 Farklı Kırılım Türü)
            is_breakout = False
            reasons = []

            # TAVAN / AŞIRI PRİMLİ HİSSE KORUMASI:
            # Hisse zaten +%6.5 ve üzeri primlenmişse (tavan bölgesindeyse), alım kapalıdır ve seans içi marj kalmamıştır.
            if change_pct >= 6.5:
                return {
                    "symbol": symbol,
                    "is_breakout": False,
                    "status": "TAVAN_TUZAGI",
                    "status_label": "TAVAN / ALIM KAPANMIŞ",
                    "breakout_score": 0.0,
                    "fakeout_risk": 99.0,
                    "reasons": ["Hisse tavan seviyesindedir (+%6.5+); seans içi alım fırsatı kalmamıştır."],
                    "metrics": {
                        "resistance_level": round(local_resistance, 2),
                        "close_price": round(c, 2),
                        "change_pct": round(change_pct, 2),
                        "relative_volume": round(rel_vol, 2),
                        "rsi": 95.0
                    }
                }

            # A) Klasik Direnç Kırılımı (10g veya 20g direnci aşıldı)
            if c > res_10d:
                is_breakout = True
                reasons.append(f"10 günlük direnç (₺{res_10d:.2f}) yukarı kırıldı")
            elif c > res_20d:
                is_breakout = True
                reasons.append(f"20 günlük direnç (₺{res_20d:.2f}) yukarı kırıldı")

            # B) Volatilite / Bollinger Üst Bandı Kırılımı
            if c >= c_bb_upper * 0.998 and rel_vol >= 1.1:
                is_breakout = True
                if not any("direnç" in r for r in reasons):
                    reasons.append("Bollinger üst bandı hacimli aşıldı")

            # C) Güçlü Momentum / Erken Kopuş Kırılımı (Pozitif +%2.5 ve 5 günlük zirve)
            lb_5 = min(len(high) - 1, 5)
            high_5d = float(high.iloc[-lb_5-1:-1].max()) if lb_5 > 1 else h
            if change_pct >= 2.5 and c >= high_5d and rel_vol >= 1.2:
                is_breakout = True
                if not reasons:
                    reasons.append("Erken momentum ve hacim patlamasıyla kopuş başladı")

            if not is_breakout:
                return self._default_result(symbol, "NO_BREAKOUT")

            # 3. KIRILIM KALİTESİ PUANLAMASI (Breakout Quality: 0 - 100)
            breakout_score = 0.0

            # Hacim Gücü (0 - 35 Puan)
            if rel_vol >= 2.0:
                breakout_score += 35.0
                reasons.append("Çok yüksek hacim patlaması (Alıcı baskısı)")
            elif rel_vol >= 1.3:
                breakout_score += 22.0
                reasons.append("Ortalama üzeri güçlü hacim desteği")
            elif rel_vol >= 1.0:
                breakout_score += 10.0
                reasons.append("Hacim ortalamayı aştı")

            # Mum Gövdesi & Kapanış Gücü (0 - 25 Puan)
            candle_range = h - l
            if candle_range > 0:
                close_position = (c - l) / candle_range
                if close_position >= 0.75:
                    breakout_score += 25.0
                    reasons.append("Günün en yükseğine yakın kapandı (Güçlü Alıcılar)")
                elif close_position >= 0.55:
                    breakout_score += 15.0
            else:
                breakout_score += 10.0

            # Trend & EMA Konumu (0 - 20 Puan)
            ema20 = close.ewm(span=20, min_periods=5).mean()
            ema50 = close.ewm(span=50, min_periods=10).mean()
            c_ema20 = float(ema20.iloc[-1])
            c_ema50 = float(ema50.iloc[-1])
            if c > c_ema20 and c_ema20 > c_ema50:
                breakout_score += 20.0
            elif c > c_ema20:
                breakout_score += 12.0

            # RSI Momentum (0 - 20 Puan)
            delta = close.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14, min_periods=5).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14, min_periods=5).mean()
            rs = gain / loss.replace(0, np.nan)
            rsi = 100 - (100 / (1 + rs))
            current_rsi = float(rsi.iloc[-1]) if len(rsi) > 0 and not pd.isna(rsi.iloc[-1]) else 55.0

            if 52 <= current_rsi <= 75:
                breakout_score += 20.0 # İdeal kırılım bölgesi
            elif current_rsi > 75:
                breakout_score += 10.0 # Güçlü fakat primli

            # 4. FALSE BREAKOUT RİSKİ (Tuzak Riski: 0 - 100)
            fakeout_risk = 0.0

            # A) Hacimsiz kırılım
            if rel_vol < 0.80:
                fakeout_risk += 25.0
                reasons.append("Tuzak Riski: Hacim desteği zayıf")

            # B) Üst fitil uzunluğu (Satıcılar bastırdı mı?)
            if candle_range > 0:
                upper_wick = h - max(c, o)
                wick_ratio = upper_wick / candle_range
                if wick_ratio > 0.45:
                    fakeout_risk += 25.0
                    reasons.append("Tuzak Riski: Üst fitil uzun (Satış baskısı geldi)")

            # C) Piyasa Rejimi Etkisi (Dengeli ve makul ceza)
            if market_regime in ["STRONG_BEAR"]:
                fakeout_risk += 20.0
                reasons.append("Piyasada sert satış baskısı mevcut")
            elif market_regime in ["BEAR"]:
                fakeout_risk += 10.0
                reasons.append("Piyasa düşüş eğiliminde")
            elif market_regime == "HIGH_VOLATILITY":
                fakeout_risk += 10.0
                reasons.append("Piyasada yüksek volatilite dalgalanması")

            # D) Aşırı Uzama (RSI > 82)
            if current_rsi > 82:
                fakeout_risk += 20.0
                reasons.append("Tuzak Riski: Aşırı alım bölgesi (Düzeltme riski)")

            breakout_score = min(100.0, float(breakout_score))
            fakeout_risk = min(100.0, float(fakeout_risk))

            # Durum Sınıflandırması
            status = "CONFIRMED_BREAKOUT"
            if breakout_score < 45 or fakeout_risk >= 45:
                status = "SUSPICIOUS_BREAKOUT"
            if fakeout_risk >= 65:
                status = "LIKELY_FAKEOUT"

            return {
                "symbol": symbol,
                "is_breakout": is_breakout,
                "status": status,
                "status_label": self.STATUS_TR_MAP.get(status, status),
                "breakout_score": round(breakout_score, 1),
                "fakeout_risk": round(fakeout_risk, 1),
                "reasons": reasons,
                "metrics": {
                    "resistance_level": round(local_resistance, 2),
                    "close_price": round(c, 2),
                    "change_pct": round(change_pct, 2),
                    "relative_volume": round(rel_vol, 2),
                    "rsi": round(current_rsi, 1)
                }
            }

        except Exception as e:
            print(f"[V8 Breakout Engine] Error on {symbol}: {e}")
            return self._default_result(symbol, "ERROR")

    def _default_result(self, symbol, status):
        return {
            "symbol": symbol,
            "is_breakout": False,
            "status": status,
            "status_label": self.STATUS_TR_MAP.get(status, status),
            "breakout_score": 0.0,
            "fakeout_risk": 0.0,
            "reasons": [],
            "metrics": {
                "resistance_level": 0.0,
                "close_price": 0.0,
                "change_pct": 0.0,
                "relative_volume": 1.0,
                "rsi": 50.0
            }
        }
