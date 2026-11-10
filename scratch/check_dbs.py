import sqlite3
import glob

print("Checking sqlite databases:")
for db in glob.glob("**/*.db", recursive=True):
    try:
        conn = sqlite3.connect(db)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in cursor.fetchall()]
        print(f"DB: {db} -> Tables: {tables}")
        if 'app_users' in tables:
            cursor.execute("SELECT * FROM app_users")
            users = cursor.fetchall()
            print(f"  app_users: {users}")
        if 'trades' in tables:
            cursor.execute("SELECT count(*), max(date_str) FROM trades")
            cnt = cursor.fetchone()
            print(f"  trades count: {cnt}")
        conn.close()
    except Exception as e:
        print(f"Error {db}: {e}")
