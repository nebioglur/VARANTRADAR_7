import numpy as np
import pandas as pd


class BacktestEngine:
    """Long-only close-signal / next-bar execution backtest.

    This vectorized engine does not model intrabar stop/target ordering. Use the
    event-driven simulator for OHLC stop/target tests.
    """

    def __init__(
        self,
        initial_capital: float = 100000.0,
        commission: float = 0.001,
        slippage_bps: float = 0.0,
    ):
        if not np.isfinite(initial_capital) or initial_capital <= 0:
            raise ValueError("initial_capital must be finite and positive")
        if not np.isfinite(commission) or commission < 0:
            raise ValueError("commission must be finite and non-negative")
        if not np.isfinite(slippage_bps) or slippage_bps < 0:
            raise ValueError("slippage_bps must be finite and non-negative")
        self.initial_capital = float(initial_capital)
        self.commission = float(commission)
        self.slippage_bps = float(slippage_bps)

    def run_backtest(self, df: pd.DataFrame, signals: pd.Series) -> pd.DataFrame:
        if df is None or df.empty:
            raise ValueError("OHLC input is empty")
        if not isinstance(signals, pd.Series):
            raise TypeError("signals must be a pandas Series")
        if not df.index.is_monotonic_increasing or df.index.has_duplicates:
            raise ValueError("OHLC index must be sorted and unique")
        close_col = "Close" if "Close" in df.columns else "close" if "close" in df.columns else None
        if close_col is None:
            raise ValueError("Close column is required")
        close = pd.to_numeric(df[close_col], errors="coerce")
        aligned = pd.to_numeric(signals.reindex(df.index), errors="coerce")
        if close.isna().any() or aligned.isna().any():
            raise ValueError("Missing or non-numeric close/signal values; no silent fill is allowed")
        if not np.isfinite(close.to_numpy(dtype=float)).all() or (close <= 0).any():
            raise ValueError("Close prices must be finite and positive")
        if not aligned.isin([-1, 0, 1]).all():
            raise ValueError("Signals must be -1, 0, or 1")

        # Signal at close[t] executes at close[t+1]. It cannot earn the
        # close[t] -> close[t+1] move; exposure for that return is the position
        # already held at close[t], i.e. executed.shift(1).
        desired = aligned.gt(0).astype(float)
        executed = desired.shift(1).fillna(0.0)
        return_exposure = executed.shift(1).fillna(0.0)
        asset_returns = close.pct_change(fill_method=None).fillna(0.0)

        # Charge entry and exit turnover on the actual execution bar.
        turnover = executed.diff().abs()
        turnover.iloc[0] = executed.iloc[0]
        transaction_cost = turnover.fillna(0.0) * (
            self.commission + self.slippage_bps / 10000.0
        )
        strategy_returns = return_exposure * asset_returns - transaction_cost

        # Guard against impossible losses from excessive modeled costs.
        strategy_returns = strategy_returns.clip(lower=-1.0)
        result = pd.DataFrame(index=df.index)
        result["close"] = close
        result["signal"] = aligned
        result["position"] = executed
        result["return_exposure"] = return_exposure
        result["asset_returns"] = asset_returns
        result["turnover"] = turnover.fillna(0.0)
        result["transaction_cost"] = transaction_cost
        result["strategy_returns"] = strategy_returns
        result["strategy_equity"] = self.initial_capital * (1.0 + strategy_returns).cumprod()
        result["asset_equity"] = self.initial_capital * (1.0 + asset_returns).cumprod()
        result.attrs["execution_model"] = "signal_at_close_fill_next_bar_close_no_pre_fill_return"
        result.attrs["commission_rate"] = self.commission
        result.attrs["slippage_bps"] = self.slippage_bps
        result.attrs["intrabar_stops_supported"] = False
        return result
