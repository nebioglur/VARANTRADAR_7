import os
import sys

# server.py den alalim
with open('server.py', 'r', encoding='utf-8') as f:
    code = f.read()

import re
url_match = re.search(r'SUPABASE_URL\s*=\s*[\'"]([^\'"]+)[\'"]', code)
key_match = re.search(r'SUPABASE_PUBLISHABLE_KEY\s*=\s*[\'"]([^\'"]+)[\'"]', code)

if not url_match or not key_match:
    print("URL or KEY not found")
    sys.exit(1)

url = url_match.group(1)
key = key_match.group(1)

from supabase import create_client, Client
supabase: Client = create_client(url, key)

tables_to_test = ['trades', 'v8_signals', 'tavan_audits', 'dashboard_cache', 'signals']

for tbl in tables_to_test:
    try:
        res = supabase.table(tbl).select("*").limit(1).execute()
        print(f"TABLE {tbl} EXISTS! Data len: {len(res.data)}")
    except Exception as e:
        print(f"TABLE {tbl} ERROR: {e}")
