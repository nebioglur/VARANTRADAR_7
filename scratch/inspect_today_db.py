import sqlite3, json

conn = sqlite3.connect('data/trading_engine.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()
cur.execute('SELECT * FROM trades WHERE date_str = "2026-11-18"')
rows = [dict(r) for r in cur.fetchall()]
print(f"Rows count: {len(rows)}")
for r in rows:
    print(r['symbol'], r['entry_time'], r['entry_price'], r['exit_time'], r['exit_price'], r['pnl_val'], r['pnl_pct'], r['exit_reason'])
