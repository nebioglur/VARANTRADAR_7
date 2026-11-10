from services.trade_database import get_connection
from datetime import datetime

conn = get_connection()
cur = conn.cursor()
d_str = datetime.now().strftime("%Y-%m-%d")
cur.execute("SELECT count(*) FROM market_data WHERE date_str=%s", (d_str,))
print("Postgres rows for today:", cur.fetchone()[0])
