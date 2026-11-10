import sys, os
sys.path.insert(0, os.getcwd())
from services.market_data import MarketDataManager

print("Testing fetch_and_store_intraday for 2026-11-05...")
MarketDataManager.fetch_and_store_intraday("2026-11-05", period="5d")
print("Done.")
