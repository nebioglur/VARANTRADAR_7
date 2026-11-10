import sys, os
sys.path.insert(0, os.path.abspath('.'))

import json
from services.simulation_engine import SimulationEngine
from services.market_data import MarketDataManager

date_str = "2026-11-10"

# Check signals
sigs = MarketDataManager.get_signals(date_str)
print(f"Signals for {date_str}: {len(sigs)}")

if not sigs:
    # Let's see why: populate from dashboard_cache.json
    with open('dashboard_cache.json', encoding='utf-8') as f:
        dash_data = json.load(f)
    stats = dash_data.get('all_symbols_stats', {})
    all_cands = []
    for sym, st in stats.items():
        if not isinstance(st, dict): continue
        p = float(st.get('Price') or st.get('Daily_Close') or 0)
        ch = float(st.get('Change_Pct') or 0)
        v = float(st.get('Vol_Multiplier') or st.get('Volume_Ratio') or 0)
        if p >= 4.0 and 0.5 <= ch < 5.2 and v >= 1.2:
            cand = dict(st)
            cand['symbol'] = sym
            cand['score'] = float(st.get('Score') or 92.0)
            cand['morning_price'] = p
            all_cands.append(cand)
    print(f"Candidate count to record: {len(all_cands)}")
    MarketDataManager.record_signals(date_str, all_cands)
    sigs = MarketDataManager.get_signals(date_str)
    print(f"After recording, signals count: {len(sigs)}")

# Now run simulation
sim = SimulationEngine(owner="local:nebioglur")
sim.run_daily_simulation(date_str)

# Now check trades in DB
from services.trade_database import get_connection
with get_connection() as conn:
    c = conn.cursor()
    c.execute("SELECT symbol, date_str, entry_time, entry_price, status, realized_pnl, pnl_val FROM trades WHERE date_str=?", (date_str,))
    rows = c.fetchall()
    print(f"Trades created for {date_str}: {len(rows)}")
    for r in rows:
        print(dict(r))
