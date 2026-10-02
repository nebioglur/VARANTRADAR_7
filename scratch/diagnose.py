import sys
import os
import sqlite3

def check_db():
    print("=== TRADING ENGINE DB ===")
    if not os.path.exists("data/trading_engine.db"):
        print("trading_engine.db NOT FOUND!")
        return
        
    conn = sqlite3.connect("data/trading_engine.db")
    c = conn.cursor()
    
    for table in ["signals", "market_data", "trades", "equity_log"]:
        try:
            c.execute(f"SELECT COUNT(*) FROM {table}")
            print(f"{table} count: {c.fetchone()[0]}")
        except Exception as e:
            print(f"Error checking {table}: {e}")

check_db()
