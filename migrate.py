import sqlite3
import os
from config.settings import DB_PATH

def run_migration():
    if not os.path.exists(DB_PATH):
        print("Veritabanı yok, migration atlanıyor.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Check if portfolio_name exists in portfolio
        cursor.execute("PRAGMA table_info(portfolio)")
        columns = [col[1] for col in cursor.fetchall()]
        if 'portfolio_name' not in columns:
            cursor.execute("ALTER TABLE portfolio ADD COLUMN portfolio_name TEXT DEFAULT 'Ana Portföy'")
            print("portfolio tablosuna portfolio_name eklendi.")
            
        # Check if portfolio_name exists in active_positions
        cursor.execute("PRAGMA table_info(active_positions)")
        columns = [col[1] for col in cursor.fetchall()]
        if 'portfolio_name' not in columns:
            cursor.execute("ALTER TABLE active_positions ADD COLUMN portfolio_name TEXT DEFAULT 'Ana Portföy'")
            print("active_positions tablosuna portfolio_name eklendi.")
            
        # Check if portfolio_name exists in trade_journal
        cursor.execute("PRAGMA table_info(trade_journal)")
        columns = [col[1] for col in cursor.fetchall()]
        if 'portfolio_name' not in columns:
            cursor.execute("ALTER TABLE trade_journal ADD COLUMN portfolio_name TEXT DEFAULT 'Ana Portföy'")
            print("trade_journal tablosuna portfolio_name eklendi.")
            
        conn.commit()
        print("Migration başarılı.")
    except Exception as e:
        print(f"Migration hatası: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    run_migration()
