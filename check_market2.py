import sqlite3
import pandas as pd
from datetime import datetime

d_str = datetime.now().strftime("%Y-%m-%d")
conn = sqlite3.connect('data/trading_engine.db')
c = conn.cursor()
c.execute("SELECT count(*) FROM market_data WHERE date_str=?", (d_str,))
print(f"market_data rows for today: {c.fetchone()[0]}")
