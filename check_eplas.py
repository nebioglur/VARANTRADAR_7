import sqlite3

con = sqlite3.connect('data/trading_engine.db')
cur = con.cursor()
cur.execute("SELECT * FROM trades WHERE symbol LIKE '%EPLAS%' ORDER BY id DESC LIMIT 10;")
rows = cur.fetchall()
print('EPLAS in trades:', len(rows))
for r in rows:
    print(r)

print('--- Last 10 trades in database ---')
cur.execute("SELECT id, date_str, symbol, entry_time, exit_time, pnl_val, pnl_pct, exit_reason FROM trades ORDER BY id DESC LIMIT 10;")
for r in cur.fetchall():
    print(r)

print('--- live_positions table ---')
cur.execute("SELECT * FROM live_positions;")
for r in cur.fetchall():
    print(r)
