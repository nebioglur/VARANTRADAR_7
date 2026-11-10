import json
from services.trade_database import get_connection

conn = get_connection()
c = conn.cursor()
c.execute("SELECT owner, date_str, symbol, entry_time, entry_price, exit_time, exit_price, pnl_pct, exit_reason FROM trades WHERE date_str='2026-11-10'")
rows = c.fetchall()
print(f"Total rows for 2026-11-10: {len(rows)}")
for r in rows:
    print(dict(r))
conn.close()
