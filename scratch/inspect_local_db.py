import sqlite3, os
for db in ['data/trading_engine.db', 'data/v8_signals.db']:
    if os.path.exists(db):
        c = sqlite3.connect(db)
        c.row_factory = sqlite3.Row
        tables = [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        print('==', db, tables)
        for t in tables:
            try:
                print('  ', t, c.execute('SELECT COUNT(*) FROM "%s"' % t).fetchone()[0])
            except Exception as e:
                print('  ', t, 'ERR', e)
        c.close()
    else:
        print('YOK', db)
