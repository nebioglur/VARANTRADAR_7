import sys, os
sys.path.insert(0, os.path.abspath('.'))
sys.stdout.reconfigure(encoding='utf-8')

from services.simulation_engine import SimulationEngine
from services.market_data import MarketDataManager

date_str = '2026-09-03'
print("Getting signals...", flush=True)
signals = MarketDataManager.get_signals(date_str)
print(f"Got {len(signals)} signals.", flush=True)

sim = SimulationEngine(owner='local:nebioglur')
print("Starting run_daily_simulation...", flush=True)
sim.run_daily_simulation(date_str)
print("Finished run_daily_simulation.", flush=True)

import sqlite3
conn = sqlite3.connect('data/trading_engine.db')
c = conn.cursor()
c.execute("SELECT count(*) FROM trades")
print("Trades count in DB now:", c.fetchone()[0], flush=True)
c.execute("SELECT symbol, entry_time, entry_price, exit_time, exit_price, pnl_pct, exit_reason FROM trades")
for r in c.fetchall():
    print("Trade:", r, flush=True)
conn.close()
