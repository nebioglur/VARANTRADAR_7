# -*- coding: utf-8 -*-
with open('server.py', 'r', encoding='utf-8') as f:
    content = f.read()

import re

old_start = '''if __name__ == '__main__':
    print(f"[SERVER] Flask baslatiliyor... BIST 50 Taramasi (Arka Plan) tetiklenecek.")'''

new_start = '''def auto_create_tables():
    try:
        import os
        from services import pg_store
        db_url = os.environ.get("DATABASE_URL", "")
        if db_url and pg_store.IS_PG:
            conn = pg_store.connect()
            cur = conn.cursor()
            cur.execute("CREATE TABLE IF NOT EXISTS tavan_audits (id TEXT PRIMARY KEY, value JSONB)")
            cur.execute("CREATE TABLE IF NOT EXISTS dashboard_cache (id TEXT PRIMARY KEY, value JSONB)")
            conn.commit()
            conn.close()
            print("[AUTO-DB] Supabase (Postgres) tablolari otomatik dogrulandi/olusturuldu!")
    except Exception as e:
        print(f"[AUTO-DB] Tablo olusturma hatasi: {e}")

if __name__ == '__main__':
    auto_create_tables()
    print(f"[SERVER] Flask baslatiliyor... BIST 50 Taramasi (Arka Plan) tetiklenecek.")'''

content = content.replace(old_start, new_start)
with open('server.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("PATCH_AUTO_DB_OK")
