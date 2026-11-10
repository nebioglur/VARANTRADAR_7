from services.market_data import MarketDataManager
from datetime import datetime

d_str = datetime.now().strftime("%Y-%m-%d")
signals = MarketDataManager.get_signals(d_str)
print(f"Total signals today ({d_str}): {len(signals)}")
for s in signals[:5]:
    print(s['symbol'], "Score:", s['score'], "Phase:", s['morning_phase'])
