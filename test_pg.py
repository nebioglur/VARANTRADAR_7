import psycopg2
try:
    conn = psycopg2.connect("postgresql://postgres:1Q2w3e4r5t6y..225-@db.kfslwkmrnjqxirzhfmbn.supabase.co:5432/postgres")
    print("CONNECTION SUCCESS!")
    conn.close()
except Exception as e:
    print(f"ERROR: {e}")
