import sqlite3
import pandas as pd
conn = sqlite3.connect('data/trading_engine.db')
print("Tables:", pd.read_sql_query("SELECT name FROM sqlite_master WHERE type='table'", conn)['name'].tolist())
try:
    print("Simulated Trades count:", pd.read_sql_query("SELECT count(*) FROM simulated_trades", conn).iloc[0,0])
    print("Recent trades:")
    print(pd.read_sql_query("SELECT * FROM simulated_trades ORDER BY id DESC LIMIT 2", conn))
except Exception as e:
    print("Error reading simulated_trades:", e)
