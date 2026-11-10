import sys, os
sys.path.insert(0, os.getcwd())
from services.market_data import MarketDataManager
import json

signals = MarketDataManager.get_signals("2026-11-05")
print(f"Total signals for 2026-11-05: {len(signals)}")
for s in signals:
    print("Signal:", s.get('symbol'), "Score:", s.get('score'), "Phase:", s.get('morning_phase'))
