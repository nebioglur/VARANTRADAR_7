import json
import os
import sqlite3

def check_arge():
    print("=== ARGE TABLOSU ===")
    if os.path.exists("data/dashboard_cache.json"):
        with open("data/dashboard_cache.json", "r") as f:
            data = json.load(f)
            tavan = data.get("tavan_adaylari", [])
            print(f"Tavan Adaylari count: {len(tavan)}")
            if tavan:
                first = tavan[0]
                keys = ["Alpha_Str", "Smart_Money", "Short_Squeeze", "Domino_Str", "P_Score"]
                for k in keys:
                    print(f"{k}: {first.get(k, 'MISSING')}")
    else:
        print("dashboard_cache.json not found")

def check_sim():
    print("\n=== SIMULASYON ===")
    if os.path.exists("data/varantradar.db"):
        conn = sqlite3.connect("data/varantradar.db")
        c = conn.cursor()
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sim_trades'")
        if not c.fetchone():
            print("Table sim_trades MISSING")
            return
        
        c.execute("SELECT date_str, json_extract(trade_data, '$') FROM sim_trades ORDER BY id DESC LIMIT 1")
        row = c.fetchone()
        if row:
            print(f"Latest sim date: {row[0]}")
            trades = json.loads(row[1])
            print(f"Trades count: {len(trades)}")
        else:
            print("sim_trades is EMPTY")
    else:
        print("varantradar.db not found")

def check_stats():
    print("\n=== ISTATISTIK ===")
    if os.path.exists("data/tavan_daily_audit.json"):
        with open("data/tavan_daily_audit.json", "r") as f:
            audit = json.load(f)
            print(f"Audit file size: {len(audit)} records")
            for k, v in audit.items():
                print(f"Sample date: {k}, keys: {list(v.keys())}")
                break
    else:
        print("tavan_daily_audit.json not found")

check_arge()
check_sim()
check_stats()
