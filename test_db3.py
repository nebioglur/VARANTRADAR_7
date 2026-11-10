import sqlite3
import pandas as pd
conn = sqlite3.connect('data/trading_engine.db')
try:
    print("Trades count:", pd.read_sql_query("SELECT count(*) FROM trades", conn).iloc[0,0])
    print("Recent trades:")
    print(pd.read_sql_query("SELECT * FROM trades ORDER BY id DESC LIMIT 5", conn).to_dict(orient="records"))
except Exception as e:
    print("Error reading trades:", e)
