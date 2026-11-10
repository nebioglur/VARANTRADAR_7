import sys, os
sys.path.insert(0, os.path.abspath('.'))

import json
from services.trade_database import get_connection

with get_connection() as conn:
    c = conn.cursor()
    c.execute("SELECT symbol, date_str, score, morning_phase, morning_price FROM signals WHERE date_str='2026-11-10'")
    rows = c.fetchall()
    print('Signals in local DB for 2026-11-10:', len(rows))
    for r in rows[:10]:
        print(dict(r))
