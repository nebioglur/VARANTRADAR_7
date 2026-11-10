import sqlite3

conn = sqlite3.connect('data/trading_engine.db')
c = conn.cursor()
c.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in c.fetchall()]
print('Tables in trading_engine.db:', tables)
if 'trades' in tables:
    c.execute("SELECT COUNT(id), status FROM trades GROUP BY status")
    print('Trades by status:', c.fetchall())
    c.execute("SELECT symbol, trade_type, entry_price, exit_price, pnl_pct, status, entry_time, exit_time FROM trades ORDER BY id DESC LIMIT 5")
    print('Recent trades:')
    for r in c.fetchall():
        print(' ', r)
