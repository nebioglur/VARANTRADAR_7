from services.trade_database import get_connection
import sys

sys.stdout.reconfigure(encoding='utf-8')
conn = get_connection()
c = conn.cursor()
c.execute("SELECT date_str, symbol, entry_time, exit_time, pnl_pct, exit_reason FROM trades ORDER BY rowid DESC LIMIT 15")
rows = c.fetchall()
for r in rows:
    print(dict(r))
conn.close()
