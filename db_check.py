import sqlite3; conn = sqlite3.connect('database/radar.db'); print(conn.cursor().execute('SELECT name FROM sqlite_master WHERE type=\'table\'').fetchall())
