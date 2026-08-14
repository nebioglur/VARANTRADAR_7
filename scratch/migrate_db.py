import json
import os
from services.trade_database import get_connection

def migrate_old_audit():
    try:
        with open('data/tavan_daily_audit.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print("No old audit data found.")
        return

    conn = get_connection()
    cursor = conn.cursor()
    
    count = 0
    for date_str, items in data.items():
        if isinstance(items, dict) and 'items' in items:
            for item in items['items']:
                sym = item.get('symbol', '')
                if not sym: continue
                if not sym.endswith('.IS'): sym += '.IS'
                
                score = 80 # Default if not found
                morning_price = item.get('morning_price', 0)
                ceiling_target = item.get('ceiling_target', morning_price * 1.10)
                morning_phase = "BELİRSİZ"
                
                try:
                    cursor.execute("""
                        INSERT INTO signals (date_str, symbol, score, morning_price, ceiling_target, morning_phase, metadata)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(date_str, symbol) DO NOTHING
                    """, (date_str, sym, score, morning_price, ceiling_target, morning_phase, "{}"))
                    count += 1
                except Exception as e:
                    pass
                    
    conn.commit()
    conn.close()
    print(f"Migrated {count} old signals to SQLite.")

if __name__ == "__main__":
    migrate_old_audit()
