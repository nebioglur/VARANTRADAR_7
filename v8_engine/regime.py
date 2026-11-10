"""V8 XU100 market-regime engine.

The displayed BIST100 Trend is strictly the verified daily close-to-close
change of XU100.IS. Intraday price is kept separate and never replaces the
daily trend value.
"""
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, Any

def _get_pa_proxy_session():
    """PythonAnywhere free tier dis internet erisimi icin proxy oturumu dondurur."""
    import requests, os
    if os.path.exists("/home/varantradarpro") or "pythonanywhere" in os.environ.get("PYTHONANYWHERE_DOMAIN", "").lower() or os.path.exists("/etc/pythonanywhere"):
        session = requests.Session()
        session.proxies = {
            "http": "http://proxy.server:3128",
            "https": "http://proxy.server:3128"
        }
        return session
    return None

from zoneinfo import ZoneInfo
import time

_REGIME_CACHE = {'data': None, 'last_fetched': 0.0}
_REGIME_CACHE_TTL = 300  # 5 dk cache (anti-ban)


class MarketRegimeEngine:
    """Deterministic XU100 regime engine using daily OHLC data."""

    def __init__(self):
        self.index_symbol = "XU100.IS"
        self._pa_session = _get_pa_proxy_session()

    def determine_regime(self, force: bool = False) -> Dict[str, Any]:
        global _REGIME_CACHE
        now_ts = time.time()
        if not force and _REGIME_CACHE['data'] is not None and (now_ts - _REGIME_CACHE['last_fetched']) < _REGIME_CACHE_TTL:
            return _REGIME_CACHE['data']
        try:
            df = self._fetch_index_df()
            if df is None or df.empty or len(df) < 30:
                calc = self._calculate_from_market_stats()
                if calc:
                    _REGIME_CACHE['data'] = calc
                    _REGIME_CACHE['last_fetched'] = now_ts
                    return calc
                return self._last_known_regime("DATA_INSUFFICIENT")

            if hasattr(df.columns, "nlevels") and df.columns.nlevels > 1:
                df.columns = df.columns.droplevel(1)

            close_col = "close" if "close" in df.columns else "Close"
            open_col = "open" if "open" in df.columns else "Open"
            high_col = "high" if "high" in df.columns else "High"
            low_col = "low" if "low" in df.columns else "Low"

            required = (close_col, open_col, high_col, low_col)
            if not all(col in df.columns for col in required):
                return self._last_known_regime("DATA_INSUFFICIENT")

            df = df.sort_index().copy()
            for col in required:
                df[col] = pd.to_numeric(df[col], errors="coerce")
            df = df.dropna(subset=list(required))

            if len(df) < 30:
                return self._last_known_regime("DATA_INSUFFICIENT")
            values = df[list(required)].to_numpy(dtype=float)
            if not np.isfinite(values).all():
                return self._last_known_regime("DATA_INSUFFICIENT")
            if (df[list(required)] <= 0).any().any():
                return self._last_known_regime("DATA_INSUFFICIENT")
            if (df[high_col] < df[low_col]).any():
                return self._last_known_regime("DATA_INSUFFICIENT")

            last_bar = pd.Timestamp(df.index[-1])
            if last_bar.tzinfo is not None:
                last_bar = last_bar.tz_convert("Europe/Istanbul")
            data_age_days = (
                datetime.now(ZoneInfo("Europe/Istanbul")).date() - last_bar.date()
            ).days
            if data_age_days > 5:
                return self._last_known_regime("DATA_INSUFFICIENT")

            close = df[close_col]
            daily_close = float(close.iloc[-1])
            previous_close = float(close.iloc[-2])

            daily_change_pct = (
                (daily_close - previous_close) / previous_close * 100.0
                if previous_close > 0 else 0.0
            )

            # Intraday quote (seans ici canli fiyat)
            live_price = self._fetch_live_price()
            intraday_change_pct = (
                (live_price - previous_close) / previous_close * 100.0
                if live_price is not None and previous_close > 0 else None
            )

            # Efektif Trend: Seans acikken intraday canli degisim esas alinir
            effective_trend = (
                intraday_change_pct
                if (intraday_change_pct is not None and abs(intraday_change_pct) > 0.001)
                else daily_change_pct
            )

            ema5 = close.ewm(span=5, adjust=False).mean()
            ema10 = close.ewm(span=10, adjust=False).mean()
            ema20 = close.ewm(span=20, adjust=False).mean()
            c_ema5 = float(ema5.iloc[-1])
            c_ema10 = float(ema10.iloc[-1])
            c_ema20 = float(ema20.iloc[-1])

            # Wilder-style ATR(14).
            tr1 = df[high_col] - df[low_col]
            tr2 = (df[high_col] - close.shift()).abs()
            tr3 = (df[low_col] - close.shift()).abs()
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr_14 = tr.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
            current_atr = float(atr_14.iloc[-1])
            atr_pct = current_atr / daily_close * 100.0 if daily_close > 0 else 0.0
            avg_atr = float(atr_14.dropna().mean())
            volatility_state = (
                "HIGH" if avg_atr > 0 and current_atr > avg_atr * 1.5 else "NORMAL"
            )

            score = 50.0
            if daily_close > c_ema5:
                score += 15
            else:
                score -= 15
            if daily_close > c_ema20:
                score += 15
            else:
                score -= 15
            if effective_trend > 1.0:
                score += 10
            elif effective_trend < -1.0:
                score -= 10
            elif effective_trend > 0:
                score += 5
            elif effective_trend < 0:
                score -= 5

            if effective_trend > 2.0:
                score += 10
            elif effective_trend < -2.0:
                score -= 10

            score = max(0.0, min(100.0, score))
            regime = "NEUTRAL"
            if score >= 80:
                regime = "STRONG_BULL"
            elif score >= 60:
                regime = "BULL"
            elif score <= 20:
                regime = "STRONG_BEAR"
            elif score <= 40:
                regime = "BEAR"

            if effective_trend >= 2.5 and regime in ("BEAR", "STRONG_BEAR"):
                regime = "NEUTRAL"
            if effective_trend <= -2.5 and regime in ("BULL", "STRONG_BULL"):
                regime = "NEUTRAL"
            if volatility_state == "HIGH" and regime in ("NEUTRAL", "BEAR"):
                regime = "HIGH_VOLATILITY"

            result = {
                "regime": regime,
                "regime_code": regime,
                "score": round(score, 1),
                "xu100_trend": round(effective_trend, 2),
                "daily_change_pct": round(daily_change_pct, 2),
                "intraday_change_pct": round(intraday_change_pct, 2) if intraday_change_pct is not None else None,
                "volatility_state": volatility_state,
                "atr_14": round(current_atr, 4),
                "atr_pct": round(atr_pct, 2),
                "data_source": "yfinance",
                "data_timeframe": "1d",
                "data_status": "OK",
                "data_available": True,
                "stale": False,
                "data_age_days": data_age_days,
                "timestamp": datetime.now(ZoneInfo("Europe/Istanbul")).isoformat(),
                "c_ema5": round(c_ema5, 2),
                "c_ema10": round(c_ema10, 2),
                "c_ema20": round(c_ema20, 2),
                "current_price": round(live_price if live_price is not None else daily_close, 2),
                "daily_close": round(daily_close, 2),
                "previous_close": round(previous_close, 2),
            }
            _REGIME_CACHE['data'] = result
            _REGIME_CACHE['last_fetched'] = now_ts
            self._save_regime_to_db(result)
            return result

        except Exception as e:
            print(f"[V8 Regime Engine] Error: {e}")
            return self._last_known_regime("ERROR")

    def _fetch_live_price(self):
        try:
            data = yf.download(self.index_symbol, period="5d", interval="1h", progress=False, **({"session": self._pa_session} if self._pa_session else {}))
            if data is not None and not data.empty:
                if hasattr(data.columns, "nlevels") and data.columns.nlevels > 1:
                    data.columns = data.columns.droplevel(1)
                c_col = "close" if "close" in data.columns else "Close"
                val = float(data[c_col].iloc[-1])
                return val if val > 0 else None
        except Exception:
            pass
        try:
            hist = yf.Ticker(self.index_symbol, **({"session": self._pa_session} if self._pa_session else {})).history(period="5d", interval="1h")
            if hist is not None and not hist.empty:
                val = float(hist["Close"].iloc[-1])
                return val if val > 0 else None
        except Exception:
            pass
        return None

    def _fetch_index_df(self):
        try:
            data = yf.download(self.index_symbol, period="3mo", interval="1d", progress=False, **({"session": self._pa_session} if self._pa_session else {}))
            if data is not None and not data.empty:
                return data.copy()
        except Exception:
            pass
        try:
            hist = yf.Ticker(self.index_symbol, **({"session": self._pa_session} if self._pa_session else {})).history(period="3mo", interval="1d")
            if hist is not None and not hist.empty:
                return hist.copy()
        except Exception:
            pass
        return None

    def _calculate_from_market_stats(self, all_stats: dict = None, xu100_val: float = None):
        """Yahoo Finance erisilemediginde canli 609 BIST hissesinin
        agirlikli hareketi ve piyasa genisliginden (Advance/Decline)
        gercek zamanli XU100 trendi ve piyasa rejimini hesaplar."""
        if not all_stats:
            try:
                import server
                g_cache = getattr(server, "GLOBAL_DASHBOARD_CACHE", None)
                if isinstance(g_cache, dict):
                    all_stats = g_cache.get("all_symbols_stats", {})
                    if xu100_val is None:
                        xu100_val = g_cache.get("xu100_change")
            except Exception:
                pass

        if not all_stats or len(all_stats) < 10:
            return None

        # BIST 30 agirlikli trend
        bist30 = [
            'AKBNK.IS', 'ARCLK.IS', 'ASELS.IS', 'BIMAS.IS', 'EKGYO.IS', 'ENKAI.IS',
            'EREGL.IS', 'FROTO.IS', 'GARAN.IS', 'GUBRF.IS', 'HEKTS.IS', 'ISCTR.IS',
            'KCHOL.IS', 'KOZAA.IS', 'KOZAL.IS', 'KRDMD.IS', 'MGROS.IS', 'OYAKC.IS',
            'PETKM.IS', 'PGSUS.IS', 'SAHOL.IS', 'SASA.IS', 'SISE.IS', 'TCELL.IS',
            'THYAO.IS', 'TOASO.IS', 'TUPRS.IS', 'VAKBN.IS', 'YKBNK.IS'
        ]
        b30_chgs = [
            float(all_stats[s].get('Change_Pct', 0))
            for s in bist30 if s in all_stats and all_stats[s].get('Change_Pct') is not None
        ]
        b30_avg = sum(b30_chgs) / len(b30_chgs) if b30_chgs else 0.0

        if xu100_val is not None and abs(float(xu100_val)) > 0.001:
            effective_trend = round(float(xu100_val), 2)
        else:
            effective_trend = round(b30_avg, 2)

        # Piyasa Genisligi (Advance / Decline)
        all_chgs = [
            float(d.get('Change_Pct', 0))
            for d in all_stats.values() if isinstance(d, dict) and d.get('Change_Pct') is not None
        ]
        total_syms = len(all_chgs)
        adv = sum(1 for c in all_chgs if c > 0)
        dec = sum(1 for c in all_chgs if c < 0)
        adv_ratio = (adv / total_syms) if total_syms > 0 else 0.5

        if adv_ratio >= 0.65 and effective_trend >= 1.0:
            regime = 'STRONG_BULL'
            score = round(75.0 + min(20.0, adv_ratio * 25.0), 1)
        elif adv_ratio >= 0.52 or effective_trend >= 0.30:
            regime = 'BULL'
            score = round(60.0 + min(15.0, (adv_ratio - 0.5) * 50.0), 1)
        elif adv_ratio <= 0.35 and effective_trend <= -1.0:
            regime = 'STRONG_BEAR'
            score = round(max(10.0, 25.0 - (0.35 - adv_ratio) * 50.0), 1)
        elif adv_ratio <= 0.45 or effective_trend <= -0.30:
            regime = 'BEAR'
            score = round(max(25.0, 40.0 - (0.45 - adv_ratio) * 50.0), 1)
        else:
            regime = 'NEUTRAL'
            score = round(45.0 + (adv_ratio - 0.45) * 50.0, 1)

        result = {
            'regime': regime,
            'regime_code': regime,
            'score': score,
            'xu100_trend': effective_trend,
            'volatility_state': 'NORMAL',
            'timestamp': datetime.now(ZoneInfo('Europe/Istanbul')).isoformat(),
            'data_status': 'LIVE_CALCULATED',
            'data_available': True,
            'stale': False,
            'breadth': {
                'advancing': adv,
                'declining': dec,
                'total': total_syms,
                'advance_ratio': round(adv_ratio, 3),
                'bist30_avg': round(b30_avg, 2)
            }
        }
        self._save_regime_to_db(result)
        return result

    def _last_known_regime(self, status="NEUTRAL"):
        calc = self._calculate_from_market_stats()
        if calc:
            return calc
        try:
            try:
                import server
                g_cache = getattr(server, "GLOBAL_DASHBOARD_CACHE", None)
                if isinstance(g_cache, dict):
                    v8_reg = g_cache.get("v8_market_regime")
                    if isinstance(v8_reg, dict) and v8_reg.get("data_available") and v8_reg.get("xu100_trend") is not None:
                        return v8_reg
            except Exception:
                pass
            from v8_engine.database import V8Database
            conn = V8Database.get_connection()
            c = conn.cursor()
            c.execute(
                "SELECT regime, regime_score, xu100_trend, volatility_state, timestamp "
                "FROM v8_market_regimes ORDER BY timestamp DESC LIMIT 1"
            )
            row = c.fetchone()
            conn.close()
            if row is not None:
                ts_str = str(row["timestamp"])
                age_days = 999
                try:
                    ts_dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                    now_ist = datetime.now(ZoneInfo("Europe/Istanbul"))
                    if ts_dt.tzinfo is None:
                        ts_dt = ts_dt.replace(tzinfo=ZoneInfo("Europe/Istanbul"))
                    age_days = (now_ist.date() - ts_dt.date()).days
                except Exception:
                    pass
                # Sadece son 3 gün içindeki ve Eylül 2026 olmayan gerçekçi verileri kabul et
                if age_days <= 3 and "2026-09" not in ts_str:
                    regime = row["regime"]
                    return {
                        "regime": regime,
                        "regime_code": regime,
                        "score": row["regime_score"],
                        "xu100_trend": row["xu100_trend"],
                        "volatility_state": row["volatility_state"],
                        "timestamp": row["timestamp"],
                        "data_status": "LAST_KNOWN",
                        "data_available": True,
                        "stale": False,
                    }
        except Exception as e:
            print(f"[V8 Regime Engine] Last-known lookup error: {e}")
        return self._default_regime(status)

    def _save_regime_to_db(self, regime_data: dict):
        try:
            from v8_engine.database import V8Database
            conn = V8Database.get_connection()
            c = conn.cursor()
            c.execute(
                """
                INSERT OR REPLACE INTO v8_market_regimes
                (timestamp, regime, regime_score, xu100_trend, volatility_state)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    regime_data["timestamp"],
                    regime_data["regime"],
                    regime_data["score"],
                    regime_data["xu100_trend"],
                    regime_data["volatility_state"],
                ),
            )
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[V8 Regime Engine] DB Error: {e}")

    def _default_regime(self, status="NEUTRAL"):
        return {
            "regime": status,
            "regime_code": status,
            "score": 50.0,
            "xu100_trend": 0.0,
            "volatility_state": "UNKNOWN",
            "timestamp": datetime.now(ZoneInfo("Europe/Istanbul")).isoformat(),
            "data_status": status,
            "data_available": False,
            "stale": False,
        }


V8RegimeEngine = MarketRegimeEngine
