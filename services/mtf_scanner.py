import yfinance as yf
import pandas as pd
import concurrent.futures
from core.config import BIST30_SYMBOLS

class MTFScanner:
    @staticmethod
    def _analyze_symbol(symbol: str) -> dict:
        try:
            df_1h = yf.download(symbol, period='1mo', interval='1h', progress=False)
            if df_1h.empty: return None
            df_1h.columns = [c[0] if isinstance(c, tuple) else c for c in df_1h.columns]
            
            close_1h = df_1h['Close']
            sma10 = close_1h.rolling(10).mean()
            sma20 = close_1h.rolling(20).mean()
            
            if len(close_1h) < 20: return None
            
            current_sma10 = sma10.iloc[-1]
            current_sma20 = sma20.iloc[-1]
            is_uptrend = (current_sma10 > current_sma20)
            
            if not is_uptrend: return None
                
            df_15m = yf.download(symbol, period='5d', interval='15m', progress=False)
            if df_15m.empty: return None
            df_15m.columns = [c[0] if isinstance(c, tuple) else c for c in df_15m.columns]
            
            close_15m = df_15m['Close']
            if len(close_15m) < 10: return None
            
            recent_returns = close_15m.pct_change().tail(10)
            cumulative_momentum = recent_returns.sum() * 100
            
            vol_15m = df_15m['Volume']
            avg_vol = vol_15m.tail(10).mean()
            current_vol = vol_15m.iloc[-1]
            vol_surge = (current_vol / avg_vol) if avg_vol > 0 else 0
            
            if cumulative_momentum > 0.5:
                return {
                    'Symbol': symbol,
                    'Score': min(100, 60 + cumulative_momentum * 10 + (vol_surge * 5)),
                    'Trend': 'MTF ÝVME',
                    'Momentum': f'15m Kümülatif: %{cumulative_momentum:.2f} (Hacim: {vol_surge:.1f}x)',
                    'Price': float(close_15m.iloc[-1]),
                    'Target': float(close_15m.iloc[-1] * 1.05)
                }
        except Exception as e:
            pass
        return None

    @classmethod
    def scan_pool(cls, pool: list) -> list:
        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(cls._analyze_symbol, sym) for sym in pool]
            for future in concurrent.futures.as_completed(futures):
                res = future.result()
                if res:
                    results.append(res)
        results.sort(key=lambda x: x['Score'], reverse=True)
        return results

