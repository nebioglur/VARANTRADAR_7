from services.simulation_engine import SimulationEngine
from datetime import datetime

today_str = datetime.now().strftime("%Y-%m-%d")
sim = SimulationEngine(owner="local:nebioglur")
sim.run_daily_simulation(today_str)

import sqlite3
conn = sqlite3.connect('data/trading_engine.db')
c = conn.cursor()
c.execute("SELECT symbol, entry_price, pnl_val FROM trades WHERE date_str=?", (today_str,))
rows = c.fetchall()
print(f"TRADES IN DB AFTER FIX: {len(rows)}")
for r in rows:
    print(r)
