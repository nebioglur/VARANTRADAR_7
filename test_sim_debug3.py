import json
from services.simulation_engine import SimulationEngine
from services.market_data import MarketDataManager
from datetime import datetime
today_str = datetime.now().strftime("%Y-%m-%d")

signals = MarketDataManager.get_signals(today_str)
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
        
    if float(r_vol) < 1.3:
        continue
    if not ema50 or not ema200 or not price:
        continue
    if float(price) <= float(ema50) and float(price) <= float(ema200):
        continue
        
    minimum_score = 80
    if score >= minimum_score and any(p in phase for p in ["Phase 1", "Phase 2", "Phase 3"]):
        volume_multiplier = float(meta.get('Vol_Multiplier') or meta.get('Volume_Ratio') or indicators.get('Volume_Ratio') or 0)
        no_trap = not bool(meta.get('Trap_Risk')) or (score >= 85 and volume_multiplier >= 1.5)
        
        indicators = meta.get('Indicators', {}) if isinstance(meta, dict) else {}
        rsi = float(indicators.get('RSI') or indicators.get('RSI_14') or meta.get('RSI') or 50)
        volume_ok = volume_multiplier >= 1.0 or "HACIMLI" in str(meta.get('Details', [])).upper()
        
        if no_trap and (32 <= rsi <= 82) and volume_ok:
            valid_signals.append(s['symbol'])

print(f"TRADES THAT WILL BE EXECUTED: {len(valid_signals)}")
print(valid_signals)
