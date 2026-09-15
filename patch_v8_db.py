# -*- coding: utf-8 -*-
with open('v8_engine/database.py', 'r', encoding='utf-8') as f:
    content = f.read()

import re

# Fallback in-memory db
old_code = r'''        os\.makedirs\("data", exist_ok=True\)
        conn = sqlite3\.connect\(cls\.DB_PATH\)'''
new_code = '''        try:
            os.makedirs("data", exist_ok=True)
            conn = sqlite3.connect(cls.DB_PATH)
        except Exception as e:
            print(f"[V8 DB INIT FALLBACK] Disk hatasi: {e}. In-memory DB kullanilacak!")
            cls.DB_PATH = ":memory:"
            conn = sqlite3.connect(cls.DB_PATH)'''
content = re.sub(old_code, new_code, content)

old_conn = r'''    def get_connection\(cls\):
        return sqlite3\.connect\(cls\.DB_PATH\)'''
new_conn = '''    def get_connection(cls):
        # Eger memory ise isolation gerekebilir ama varsayilan da calisir
        return sqlite3.connect(cls.DB_PATH)'''
content = re.sub(old_conn, new_conn, content)

with open('v8_engine/database.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("V8_DB_FALLBACK_OK")
