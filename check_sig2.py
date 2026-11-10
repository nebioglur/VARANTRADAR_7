from services.market_data import MarketDataManager
from datetime import datetime
import json
from services.simulation_engine import SimulationEngine

sim = SimulationEngine(owner="test")
d_str = datetime.now().strftime("%Y-%m-%d")
signals = MarketDataManager.get_signals(d_str)

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
        
    print(f"[{s['symbol']}] Score: {score}, Phase: {phase}, Price: {price}, EMA50: {ema50}, EMA200: {ema200}, R_Vol: {r_vol}")
    
    if float(r_vol) < 1.3:
        print("  -> REJECTED BY VOLUME")
        continue
        
    if not ema50 or not ema200 or not price:
        print("  -> REJECTED BY MISSING EMA/PRICE")
        continue
        
    try:
        if float(price) <= float(ema50) and float(price) <= float(ema200):
            print("  -> REJECTED BY EMA FILTER (Price below both EMA50 and EMA200)")
            continue
    except:
        continue
        
    if score >= 80 and any(p in phase for p in ["Phase 1", "Phase 2", "Phase 3"]):
        print("  -> ACCEPTED!")
    else:
        print("  -> REJECTED BY SCORE OR PHASE")

