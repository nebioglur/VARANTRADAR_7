import yfinance as yf
import pandas as pd
import numpy as np
import concurrent.futures
from config.bist_symbols import BIST_SYMBOLS


class MTFScanner:

    @staticmethod
    def _compute_indicators(df):
        """Compute EMA9, EMA21, RSI, Momentum on a dataframe."""
        if df is None or df.empty or len(df) < 20:
            return None
        close = df["Close"] if "Close" in df.columns else df["close"]
        e9  = close.ewm(span=9,  adjust=False).mean()
        e21 = close.ewm(span=21, adjust=False).mean()
        delta = close.diff()
        gain  = delta.where(delta > 0, 0).rolling(14).mean()
        loss  = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs    = gain / loss.replace(0, float("nan"))
        rsi   = 100 - (100 / (1 + rs))
        mom   = close - close.shift(10)
        return {
            "close":  float(close.iloc[-1]),
            "e9":     float(e9.iloc[-1]),
            "e21":    float(e21.iloc[-1]),
            "rsi":    float(rsi.iloc[-1]),
            "mom":    float(mom.iloc[-1]),
        }

    @classmethod
    def scan_pool(cls, pool: list, max_symbols: int = 200) -> list:
        """
        Bulk-downloads 1h data for up to max_symbols stocks,
        then checks:
          1h:  EMA9 > EMA21 (kisa vade yükselis)
          1h:  RSI > 45
          15m: cumulative return > 0 (son 10 mum)
        """
        pool = list(set(pool))[:max_symbols]  # cap to avoid timeout

        # --- Step 1: Bulk 1h download ---
        try:
            data_1h = yf.download(
                pool, period="1mo", interval="1h",
                group_by="ticker", threads=True, progress=False
            )
        except Exception:
            return []

        passed_1h = []
        for sym in pool:
            try:
                if len(pool) == 1:
                    df = data_1h.copy()
                elif hasattr(data_1h.columns, "levels") and sym in data_1h.columns.get_level_values(0):
                    df = data_1h[sym].copy()
                else:
                    continue
                df = df.dropna(how="all")
                if df.empty or len(df) < 20:
                    continue
                ind = cls._compute_indicators(df)
                if ind and ind["e9"] > ind["e21"] and ind["rsi"] > 45:
                    passed_1h.append((sym, ind["close"]))
            except Exception:
                continue

        if not passed_1h:
            return []

        # --- Step 2: Bulk 15m download for passed symbols ---
        passed_syms = [s[0] for s in passed_1h]
        price_map   = {s[0]: s[1] for s in passed_1h}
        try:
            data_15m = yf.download(
                passed_syms, period="5d", interval="15m",
                group_by="ticker", threads=True, progress=False
            )
        except Exception:
            return []

        results = []
        for sym in passed_syms:
            try:
                if len(passed_syms) == 1:
                    df15 = data_15m.copy()
                elif hasattr(data_15m.columns, "levels") and sym in data_15m.columns.get_level_values(0):
                    df15 = data_15m[sym].copy()
                else:
                    continue
                df15 = df15.dropna(how="all")
                if df15.empty or len(df15) < 10:
                    continue
                close15 = df15["Close"] if "Close" in df15.columns else df15["close"]
                vol15   = df15["Volume"] if "Volume" in df15.columns else df15["volume"]

                # Kumulatif 15m ivme (son 10 mum)
                cum_ret = close15.pct_change().tail(10).sum() * 100
                avg_vol = float(vol15.tail(20).mean())
                cur_vol = float(vol15.iloc[-1])
                vol_surge = (cur_vol / avg_vol) if avg_vol > 0 else 0

                # Sadece yukari ivmeli hisseler
                if cum_ret <= 0:
                    continue

                ind_1h = cls._compute_indicators(
                    data_1h[sym].dropna(how="all") if len(passed_syms) > 1 else data_1h.dropna(how="all")
                )
                score = min(100, 50 + cum_ret * 8 + vol_surge * 3 + (ind_1h["rsi"] - 45) * 0.5 if ind_1h else 50 + cum_ret * 8)

                if score >= 85 and vol_surge > 1.5:
                    trend_badge = "🔥 GÜÇLÜ AL"
                elif score >= 70:
                    trend_badge = "✅ HIZLI AL"
                elif score >= 60:
                    trend_badge = "⚠️ POTANSİYEL"
                else:
                    trend_badge = "⏳ İZLE"

                results.append({
                    "Symbol":   sym,
                    "Score":    round(score, 1),
                    "Price":    round(float(close15.iloc[-1]), 2),
                    "Target":   round(float(close15.iloc[-1]) * 1.05, 2),
                    "Trend":    trend_badge,
                    "Momentum": f"15m Kumulatif: %{cum_ret:.2f} | Hacim: {vol_surge:.1f}x",
                })
            except Exception:
                continue

        results.sort(key=lambda x: x["Score"], reverse=True)
        return results
