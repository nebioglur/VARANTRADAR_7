import sqlite3

conn = sqlite3.connect('data/trading_engine.db')
c = conn.cursor()
print("Tables:", [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()])

for tbl in ['trades', 'equity_log', 'simulation_resets']:
    try:
        rows = c.execute(f"SELECT * FROM {tbl}").fetchall()
        cols = [d[0] for d in c.description]
        print(f"\n--- {tbl} ({len(rows)} rows) ---")
        for r in rows:
            print(dict(zip(cols, r)))
    except Exception as e:
        print(f"Error {tbl}: {e}")
