import sqlite3

conn = sqlite3.connect('data/trading_engine.db')
c = conn.cursor()
c.execute("PRAGMA table_info(trades)")
cols = [r[1] for r in c.fetchall()]
print('Trades table columns:', cols)

c.execute("SELECT * FROM trades ORDER BY rowid DESC LIMIT 3")
rows = c.fetchall()
print('Recent rows count:', len(rows))
for r in rows:
    print(dict(zip(cols, r)))
