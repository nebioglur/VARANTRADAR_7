# -*- coding: utf-8 -*-
with open('services/trade_database.py', 'r', encoding='utf-8') as f:
    content = f.read()

import re

# importlari ekle
old_imports = '''import os'''
new_imports = '''import os
from services import pg_store as _pg_store'''
content = content.replace(old_imports, new_imports)

# get_connection guncelle
old_conn = '''def get_connection():
    global DB_FALLBACK_MEMORY
    if DB_FALLBACK_MEMORY:
        return sqlite3.connect(":memory:")
    try:
        return sqlite3.connect(DB_PATH)
    except Exception:
        DB_FALLBACK_MEMORY = True
        return sqlite3.connect(":memory:")'''

new_conn = '''def get_connection():
    if getattr(_pg_store, 'IS_PG', False):
        return _pg_store.connect()
    
    global DB_FALLBACK_MEMORY
    if DB_FALLBACK_MEMORY:
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        return conn
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception:
        DB_FALLBACK_MEMORY = True
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        return conn'''
content = content.replace(old_conn, new_conn)

with open('services/trade_database.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("PATCH_TRADE_PG_OK")
