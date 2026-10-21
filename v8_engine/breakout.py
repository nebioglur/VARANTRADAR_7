import pandas as pd
import numpy as np
from typing import Dict, Any

class BreakoutEngine:
    """
    V8 Breakout & False Breakout Engine
    Kırılımları tespit eder ve kalitesini (gerçek mi tuzak mı) detaylı puanlar.
    """
    def __init__(self):
        pass

    def analyze_breakout(self, df: pd.DataFrame, symbol: str, market_regime: str = "NEUTRAL") -> Dict[str, Any]:
        """
        Son barlardaki kırılımları analiz eder.
        """
        if df is None or len(df) < 50:
            return self._default_result(symbol, "DATA_INSUFFICIENT")

        try:
            close = df['Close'] if 'Close' in df.columns else df['close']
            high = df['High'] if 'High' in df.columns else df['high']
            low = df['Low'] if 'Low' in df.columns else df['low']
            open_p = df['Open'] if 'Open' in df.columns else df['open']
            vol = df['Volume'] if 'Volume' in df.columns else df['volume']

            if vol.sum() == 0:
                return self._default_result(symbol, "NO_VOLUME")

            c = float(close.iloc[-1])
            h = float(high.iloc[-1])
            l = float(low.iloc[-1])
            o = float(open_p.iloc[-1])
            v = float(vol.iloc[-1])

            # 1. Direnç (Resistance) Tespiti (Son 20 günün en yükseği, son 3 gün hariç)
            # Amaç: Yakın geçmişteki bir tepeyi aşıp aşmadığına bakmak.
            past_highs = high.iloc[-25:-2]
            local_resistance = float(past_highs.max())
            
            is_breakout = False
            breakout_score = 0
            fakeout_risk = 0
            reasons = []

            # 2. Kırılım Gerçekleşmiş mi?
            if c > local_resistance:
                is_breakout = True
                reasons.append("Yakın direnci aştı")

            # Alternatif Kırılım: Bollinger Üst Bandını sert kesme
            bb_mean = close.rolling(20).mean()
            bb_std = close.rolling(20).std()
            bb_upper = bb_mean + (bb_std * 2)
            c_bb_upper = float(bb_upper.iloc[-1])
            if c > c_bb_upper and float(close.iloc[-2]) <= float(bb_upper.iloc[-2]):
                is_breakout = True
                if "Bollinger üst bandını kırdı" not in reasons: reasons.append("Bollinger üst bandını kırdı")

            if not is_breakout:
                return self._default_result(symbol, "NO_BREAKOUT")

            # --- BREAKOUT QUALITY (Gerçek Kırılım Kalitesi) ---
            
            # Hacim Teyidi
            vol_sma_10 = vol.rolling(10).mean()
            avg_vol = float(vol_sma_10.iloc[-1])
            rel_vol = v / avg_vol if avg_vol > 0 else 1

            if rel_vol > 2.0:
                breakout_score += 35
                reasons.append("Çok güçlü hacim patlaması")
            elif rel_vol > 1.3:
                breakout_score += 15
                reasons.append("Güçlü hacim desteği")

            # Mum Yapısı (Kapanışın mumun neresinde olduğu)
            candle_range = h - l
            if candle_range > 0:
                close_position = (c - l) / candle_range # 0 = en dip, 1 = en tepe
                if close_position > 0.8:
                    breakout_score += 25
                    reasons.append("Tepeden kapanış (güçlü alıcılar)")
                elif close_position > 0.6:
                    breakout_score += 15
            
            # Trend Gücü
            ema20 = close.ewm(span=20).mean()
            ema50 = close.ewm(span=50).mean()
            c_ema20 = float(ema20.iloc[-1])
            c_ema50 = float(ema50.iloc[-1])
            if c_ema20 > c_ema50 and c > c_ema20:
                breakout_score += 15
                
            # RSI (Momentum)
            delta = close.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            current_rsi = float(rsi.iloc[-1])
            # 0/0 veya tum kazancli senaryolarda NaN/inf olabilir -> guvenli banda cek
            if pd.isna(current_rsi):
                current_rsi = 50.0
            current_rsi = max(0.0, min(100.0, current_rsi))

            if 60 <= current_rsi <= 75:
                breakout_score += 25 # Ideal breakout zone
            elif current_rsi > 75:
                breakout_score += 10 # Slightly overextended
            
            # --- FALSE BREAKOUT RISK (Tuzak Riski) ---
            
            # 1. Hacimsiz kırılım
            if rel_vol < 0.9:
                fakeout_risk += 40
                reasons.append("Tuzak riski: hacimsiz kırılım")
                
            # 2. Üst Fitil (Satıcılar bastırdı)
            if candle_range > 0:
                upper_wick = h - max(c, o)
                wick_ratio = upper_wick / candle_range
                if wick_ratio > 0.4:
                    fakeout_risk += 40
                    reasons.append("Tuzak riski: uzun üst fitil (satıcı baskısı)")
                    
            # 3. Market Regime Filtresi
            if market_regime in ["BEAR", "STRONG_BEAR"]:
                fakeout_risk += 30
                reasons.append("Tuzak riski: piyasa ayı rejiminde")
            elif market_regime == "HIGH_VOLATILITY":
                fakeout_risk += 20
                reasons.append("Tuzak riski: piyasada yüksek volatilite")
                
            # 4. Aşırı Uzama (RSI > 85)
            if current_rsi > 85:
                fakeout_risk += 25
                reasons.append("Tuzak riski: aşırı uzama (tükenme)")

            # Total Cap
            breakout_score = min(100.0, float(breakout_score))
            fakeout_risk = min(100.0, float(fakeout_risk))

            status = "CONFIRMED_BREAKOUT"
            if breakout_score < 50 or fakeout_risk >= 40:
                status = "SUSPICIOUS_BREAKOUT"
            if fakeout_risk >= 70:
                status = "LIKELY_FAKEOUT"

            return {
                "symbol": symbol,
                "is_breakout": is_breakout,
                "status": status,
                "breakout_score": round(breakout_score, 1),
                "fakeout_risk": round(fakeout_risk, 1),
                "reasons": reasons,
                "metrics": {
                    "resistance_level": round(local_resistance, 2),
                    "close_price": round(c, 2),
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
            "breakout_score": 0.0,
            "fakeout_risk": 0.0,
            "reasons": [],
            "metrics": {}
        }
