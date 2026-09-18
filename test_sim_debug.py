import json
from services.simulation_engine import SimulationEngine
from services.market_data import MarketDataManager
from datetime import datetime
today_str = datetime.now().strftime("%Y-%m-%d")

signals = MarketDataManager.get_signals(today_str)
print(f"Total Signals: {len(signals)}")

sim = SimulationEngine(owner="local:nebioglur")
valid_signals = []

for s in signals:
    score = float(s['score'])
    phase = str(s['morning_phase'])
    meta = json.loads(s.get('metadata', '{}'))
    price = float(meta.get('Price') or meta.get('Daily_Close') or s.get('morning_price', 0))
    
    ema50, ema200 = sim._daily_trend_values(meta, s['symbol'])
    
    v8_disc = meta.get('v8_discovery', {})
    metrics = v8_disc.get('metrics', {})
    r_vol = metrics.get('relative_volume', 0)
    if not r_vol:
        indicators = meta.get('Indicators', {}) if isinstance(meta, dict) else {}
        r_vol = float(meta.get('Vol_Multiplier') or meta.get('Volume_Ratio') or indicators.get('Volume_Ratio') or 0)
        
    print(f"\n--- {s['symbol']} ---")
    print(f"r_vol: {r_vol}, ema50: {ema50}, ema200: {ema200}, price: {price}, phase: {phase}, score: {score}")
    
    if float(r_vol) < 1.5:
        print("REJECTED: r_vol < 1.5")
        continue

    if not ema50 or not ema200 or not price:
        print("REJECTED: Missing EMA or Price")
        continue
        
    if float(price) <= float(ema50) or float(price) <= float(ema200):
        print("REJECTED: Price <= EMA")
        continue
        
    minimum_score = 85
    if score >= minimum_score and any(p in phase for p in ["Phase 1", "Phase 2", "Phase 3"]):
        print("PHASE & SCORE PASSED!")
        valid_signals.append(s)
    else:
        print("REJECTED: Phase/Score not matched")

print(f"\nTotal Valid Signals for processing: {len(valid_signals)}")
