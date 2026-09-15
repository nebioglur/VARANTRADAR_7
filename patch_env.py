# -*- coding: utf-8 -*-
with open('server.py', 'r', encoding='utf-8') as f:
    content = f.read()

import re

old_url = r"SUPABASE_URL = os\.environ\.get\('SUPABASE_URL', '.*?'\)"
new_url = r"SUPABASE_URL = os.environ.get('SUPABASE_URL', 'https://kfslwkmrnjqxirzhfmbn.supabase.co')"

old_key = r"SUPABASE_PUBLISHABLE_KEY = os\.environ\.get\('SUPABASE_PUBLISHABLE_KEY', '.*?'\)"
new_key = r"SUPABASE_PUBLISHABLE_KEY = os.environ.get('SUPABASE_PUBLISHABLE_KEY', 'sb_publishable_r2tfnmKF3dq_I1YkqGi-Bw_O38IUlEj')"

content = re.sub(old_url, new_url, content)
content = re.sub(old_key, new_key, content)

with open('server.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("SERVER YAZILDI")
