from services.market_data import MarketDataManager
from datetime import datetime

d_str = datetime.now().strftime("%Y-%m-%d")
df = MarketDataManager.get_market_data(d_str, "AKFIS.IS")
print(f"AKFIS.IS {d_str} market data rows:", len(df))

if not df.empty:
    print(df.head(2))
