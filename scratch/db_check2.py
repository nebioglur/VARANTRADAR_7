import sqlite3; conn = sqlite3.connect('data/trading_engine.db'); print('Signals count:', conn.cursor().execute('SELECT COUNT(*) FROM signals').fetchone()[0])
