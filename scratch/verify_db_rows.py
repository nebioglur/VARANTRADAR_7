import sqlite3
import json

conn = sqlite3.connect('data/trading_engine.db')
conn.row_factory = sqlite3.Row
c = conn.cursor()

owner = "local:nebioglur"
c.execute("SELECT * FROM equity_log WHERE owner=? ORDER BY date_str ASC", (owner,))
eq = [dict(r) for r in c.fetchall()]
print("Equity curve rows:", len(eq))
for r in eq:
    print(r)

c.execute("SELECT * FROM trades WHERE owner=? ORDER BY date_str DESC, entry_time DESC", (owner,))
tr = [dict(r) for r in c.fetchall()]
print("\nTrades rows:", len(tr))
for r in tr:
    safe_r = {k: (v if k != 'exit_reason' and k != 'strategy_name' else str(v)[:30]) for k, v in r.items()}
    print(safe_r)
