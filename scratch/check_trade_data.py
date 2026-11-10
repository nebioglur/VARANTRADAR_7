import sqlite3, json

db = sqlite3.connect(r'c:\Users\nebioglur\Desktop\TUM MASAUSTU_Kurtarilan\TUM MASAUSTU\VarantRadarPro\data\trading_engine.db')
db.row_factory = sqlite3.Row
cur = db.cursor()

# Check trades table structure
cur.execute("PRAGMA table_info(trades)")
cols = cur.fetchall()
print("TRADES TABLE COLUMNS:")
for c in cols:
    print(f"  {c['cid']}: {c['name']} ({c['type']})")

print()

# Check all trades
cur.execute("SELECT * FROM trades ORDER BY entry_time DESC LIMIT 10")
rows = cur.fetchall()
print(f"TRADES COUNT: {len(rows)}")
for r in rows:
    d = dict(r)
    print(f"  ID={d.get('id')} SYMBOL={d.get('symbol')} entry_price={d.get('entry_price')} exit_price={d.get('exit_price')} pnl_val={d.get('pnl_val')} pnl_pct={d.get('pnl_pct')} entry_time={d.get('entry_time')} exit_time={d.get('exit_time')}")

print()

# Check equity_log
cur.execute("SELECT COUNT(*) as cnt FROM equity_log")
eq_cnt = cur.fetchone()['cnt']
print(f"EQUITY_LOG ENTRIES: {eq_cnt}")

cur.execute("SELECT * FROM equity_log ORDER BY date DESC LIMIT 5")
for r in cur.fetchall():
    print(f"  date={dict(r).get('date')} end_equity={dict(r).get('end_equity')} daily_pnl={dict(r).get('daily_pnl')}")

db.close()
