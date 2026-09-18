import json
from services.simulation_engine import SimulationEngine
from services.market_data import MarketDataManager
from datetime import datetime
today_str = datetime.now().strftime("%Y-%m-%d")

signals = MarketDataManager.get_signals(today_str)
print(f"Total Signals in DB: {len(signals)}")

valid = []
for s in signals:
    meta = json.loads(s.get('metadata', '{}'))
    v8_disc = meta.get('v8_discovery', {})
    metrics = v8_disc.get('metrics', {})
    r_vol = metrics.get('relative_volume', 0)
    if not r_vol:
        indicators = meta.get('Indicators', {}) if isinstance(meta, dict) else {}
        r_vol = float(meta.get('Vol_Multiplier') or meta.get('Volume_Ratio') or indicators.get('Volume_Ratio') or 0)
    
    if float(r_vol) >= 1.5:
        valid.append(s['symbol'])

print(f"Signals with >= 150% volume: {len(valid)}")
print(valid)
