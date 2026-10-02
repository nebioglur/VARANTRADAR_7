# -*- coding: utf-8 -*-
import re

with open('services/tavan_tracker.py', 'r', encoding='utf-8') as f:
    content = f.read()

pg_imports = '''import json
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List
import services.pg_store as pg_store'''

content = re.sub(r'import json\s+import os\s+from datetime import datetime, timedelta\s+from typing import Dict, Any, List', pg_imports, content)

new_db_methods = '''
    @classmethod
    def _init_pg_table(cls):
        try:
            conn = pg_store.connect()
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS tavan_audits (
                    date_str TEXT PRIMARY KEY,
                    data_json TEXT
                )
            """)
            conn.commit()
            cur.close()
            conn.close()
        except Exception as e:
            print(f"[TavanTracker] PG Init Error: {e}")

    @classmethod
    def load_all_audits(cls) -> Dict[str, Any]:
        cls._init_pg_table()
        all_data = {}
        try:
            conn = pg_store.connect()
            cur = conn.cursor()
            cur.execute("SELECT date_str, data_json FROM tavan_audits")
            rows = cur.fetchall()
            for r in rows:
                all_data[r[0]] = json.loads(r[1])
            cur.close()
            conn.close()
        except Exception as e:
            print(f"[TavanTracker] PG Load Error: {e}")
        
        if not all_data:
            initial = cls._generate_initial_historical_data()
            cls.save_all_audits(initial)
            return initial
        return all_data

    @classmethod
    def save_all_audits(cls, data: Dict[str, Any]):
        cls._init_pg_table()
        try:
            conn = pg_store.connect()
            cur = conn.cursor()
            for date_str, daily_data in data.items():
                cur.execute(
                    "INSERT INTO tavan_audits (date_str, data_json) VALUES (%s, %s) ON CONFLICT (date_str) DO UPDATE SET data_json = EXCLUDED.data_json",
                    (date_str, json.dumps(daily_data))
                )
            conn.commit()
            cur.close()
            conn.close()
        except Exception as e:
            print(f"[TavanTracker] PG Save Error: {e}")
'''

# load_all_audits fonksiyonunu yenisiyle degistir
content = re.sub(r'\s*@classmethod\s*def load_all_audits\(cls\).*?return initial\s*@classmethod\s*def save_all_audits\(cls, data: Dict\[str, Any\]\):.*?print\(f"\[TavanAuditTracker\] Kayit hatasi: \{e\}"\)', new_db_methods, content, flags=re.DOTALL)

with open('services/tavan_tracker.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("PATCH_TRACKER_FINAL_OK")
