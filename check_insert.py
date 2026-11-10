from services.market_data import MarketDataManager
from datetime import datetime
import traceback

d_str = datetime.now().strftime("%Y-%m-%d")
try:
    MarketDataManager.fetch_and_store_intraday(d_str, period="1d")
except Exception as e:
    traceback.print_exc()
