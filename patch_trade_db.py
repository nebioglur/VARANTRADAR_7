# -*- coding: utf-8 -*-
with open('services/trade_database.py', 'r', encoding='utf-8') as f:
    content = f.read()

import re

old_code = r'''    os\.makedirs\("data", exist_ok=True\)
    conn = get_connection\(\)'''
new_code = '''    try:
        os.makedirs("data", exist_ok=True)
    except Exception as e:
        print(f"[TRADE DB INIT FALLBACK] Disk klasoru olusturulamadi: {e}")
    conn = get_connection()'''
content = re.sub(old_code, new_code, content)

old_conn = r'''def get_connection\(\):
    return sqlite3\.connect\(DB_PATH\)'''
new_conn = '''DB_FALLBACK_MEMORY = False
def get_connection():
    global DB_FALLBACK_MEMORY
    if DB_FALLBACK_MEMORY:
        return sqlite3.connect(":memory:")
    try:
        return sqlite3.connect(DB_PATH)
    except Exception:
        DB_FALLBACK_MEMORY = True
        return sqlite3.connect(":memory:")'''
content = re.sub(old_conn, new_conn, content)

with open('services/trade_database.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("TRADE_DB_FALLBACK_OK")
