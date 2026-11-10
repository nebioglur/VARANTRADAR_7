import sqlite3

conn = sqlite3.connect('data/trading_engine.db')
c = conn.cursor()
c.execute("SELECT sql FROM sqlite_master WHERE name='trades'")
print(c.fetchone()[0])
c.execute("PRAGMA index_list('trades')")
indices = c.fetchall()
print('Indices:', indices)
for idx in indices:
    c.execute(f"PRAGMA index_info('{idx[1]}')")
    print(f"Info for {idx[1]}:", c.fetchall())
conn.close()
