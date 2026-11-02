import pandas as pd


class WarrantEngine:
    """Use verified exchange-listed instruments only.

    No issuer/BIST instrument-master provider is configured, so the engine
    intentionally returns no contracts instead of fabricating live-looking data.
    """

    COLUMNS = [
        "warrant_code", "underlying", "type", "strike", "maturity_date",
        "days_to_maturity", "multiplier", "bid", "ask", "spread_pct",
        "delta", "gamma", "theta", "vega", "data_status",
    ]

    def generate_warrants_for_stock(self, symbol: str, current_price: float) -> pd.DataFrame:
        return pd.DataFrame(columns=self.COLUMNS)

    def evaluate_warrants(self, df: pd.DataFrame, underlying_price: float) -> pd.DataFrame:
        # Preserve caller compatibility while refusing to rank unknown instruments.
        return df.copy() if df is not None else pd.DataFrame(columns=self.COLUMNS)
