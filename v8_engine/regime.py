import yfinance as yf
import pandas as pd
from datetime import datetime
from typing import Dict, Any

class MarketRegimeEngine:
    """
    V8 Market Regime Engine
    Belirledigi rejimler: STRONG_BULL, BULL, NEUTRAL, BEAR, STRONG_BEAR, HIGH_VOLATILITY
    """
    def __init__(self):
        self.index_symbol = "XU100.IS"
        
    def determine_regime(self) -> Dict[str, Any]:
        try:
            df = self._fetch_index_df()
            if df is None or df.empty:
                return self._last_known_regime("DATA_INSUFFICIENT")

            # yfinance MultiIndex check
            if hasattr(df.columns, 'nlevels') and df.columns.nlevels > 1:
                df.columns = df.columns.droplevel(1)
                
            close_col = 'close' if 'close' in df.columns else 'Close'
            high_col = 'high' if 'high' in df.columns else 'High'
            low_col = 'low' if 'low' in df.columns else 'Low'
            
            close = df[close_col]
            current_price = float(close.iloc[-1])
            prev_price = float(close.iloc[-2]) if len(close) > 1 else current_price
            
            # EMA Hesaplamalari (1mo data oldugu icin approximation yapariz, tam deger olmayabilir, 
            # ama kisa-orta vade trend yonunu belirler)
            ema5 = close.ewm(span=5, adjust=False).mean()
            ema20 = close.ewm(span=20, adjust=False).mean()
            
            c_ema5 = float(ema5.iloc[-1])
            c_ema20 = float(ema20.iloc[-1])
            
            # Volatilite Analizi (ATR approximation)
            tr1 = df[high_col] - df[low_col]
            tr2 = abs(df[high_col] - close.shift())
            tr3 = abs(df[low_col] - close.shift())
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr_14 = tr.rolling(14).mean()
            if len(atr_14) > 0 and not pd.isna(atr_14.iloc[-1]):
                current_atr = float(atr_14.iloc[-1])
                avg_atr = float(atr_14.mean())
                volatility_state = "HIGH" if current_atr > avg_atr * 1.5 else "NORMAL"
            else:
                volatility_state = "NORMAL"
            
            # Trend Skorlamasi
            change_pct = ((current_price - prev_price) / prev_price) * 100
            
            score = 50 # Baseline Neutral
            
            if current_price > c_ema5: score += 15
            else: score -= 15
            
            if current_price > c_ema20: score += 15
            else: score -= 15
            
            if change_pct > 1.0: score += 10
            elif change_pct < -1.0: score -= 10
            elif change_pct > 0: score += 5
            elif change_pct < 0: score -= 5
            
            # Rejim Karari
            regime = "NEUTRAL"
            if score >= 80: regime = "STRONG_BULL"
            elif score >= 60: regime = "BULL"
            elif score <= 20: regime = "STRONG_BEAR"
            elif score <= 40: regime = "BEAR"
            
            if volatility_state == "HIGH" and regime in ["NEUTRAL", "BEAR"]:
                regime = "HIGH_VOLATILITY"
                
            result = {
                "regime": regime,
                "score": score,
                "xu100_trend": round(change_pct, 2),
                "volatility_state": volatility_state,
                "timestamp": datetime.now().isoformat(),
                "c_ema5": round(c_ema5, 2),
                "c_ema20": round(c_ema20, 2),
                "current_price": round(current_price, 2)
            }
            
            self._save_regime_to_db(result)
            return result
            
        except Exception as e:
            print(f"[V8 Regime Engine] Error: {e}")
            return self._last_known_regime("ERROR")

    def _fetch_index_df(self):
        """XU100 gunluk verisini ceker: once bulk download, basarisizsa Ticker fallback."""
        try:
            data = yf.download(self.index_symbol, period="3mo", interval="1d", progress=False)
            if data is not None and not data.empty:
                return data.copy()
        except Exception:
            pass
        try:
            hist = yf.Ticker(self.index_symbol).history(period="3mo", interval="1d")
            if hist is not None and not hist.empty:
                return hist.copy()
        except Exception:
            pass
        return None

    def _last_known_regime(self, status="NEUTRAL"):
        """Yahoo verisi yoksa DB'deki son bilinen rejimi dondurur; yoksa neutral default."""
        try:
            from v8_engine.database import V8Database
            conn = V8Database.get_connection()
            c = conn.cursor()
            c.execute("SELECT regime, regime_score, xu100_trend, volatility_state, timestamp FROM v8_market_regimes ORDER BY timestamp DESC LIMIT 1")
            row = c.fetchone()
            conn.close()
            if row is not None:
                return {
                    "regime": row["regime"],
                    "score": row["regime_score"],
                    "xu100_trend": row["xu100_trend"] or 0.0,
                    "volatility_state": row["volatility_state"] or "NORMAL",
                    "timestamp": row["timestamp"],
                    "stale": True
                }
        except Exception as e:
            print(f"[V8 Regime Engine] Last-known lookup error: {e}")
        return self._default_regime(status)

    def _save_regime_to_db(self, regime_data: dict):
        try:
            from v8_engine.database import V8Database
            conn = V8Database.get_connection()
            c = conn.cursor()
            c.execute('''
                INSERT OR REPLACE INTO v8_market_regimes (timestamp, regime, regime_score, xu100_trend, volatility_state)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                regime_data["timestamp"],
                regime_data["regime"],
                regime_data["score"],
                regime_data["xu100_trend"],
                regime_data["volatility_state"]
            ))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[V8 Regime Engine] DB Error: {e}")

    def _default_regime(self, status="NEUTRAL"):
        return {
            "regime": status,
            "score": 50.0,
            "xu100_trend": 0.0,
            "volatility_state": "UNKNOWN",
            "timestamp": datetime.now().isoformat()
        }
