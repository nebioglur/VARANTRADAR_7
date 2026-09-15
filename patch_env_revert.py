# -*- coding: utf-8 -*-
with open('server.py', 'r', encoding='utf-8') as f:
    content = f.read()

import re

old_url = r"SUPABASE_URL = os\.environ\.get\('SUPABASE_URL', '.*?'\)"
new_url = r"SUPABASE_URL = os.environ.get('SUPABASE_URL', 'https://supabase-api-prod.verdent.ai/p/p4c2618bf93ce4a2f45f8')"

old_key = r"SUPABASE_PUBLISHABLE_KEY = os\.environ\.get\('SUPABASE_PUBLISHABLE_KEY', '.*?'\)"
new_key = r"SUPABASE_PUBLISHABLE_KEY = os.environ.get('SUPABASE_PUBLISHABLE_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoyMTA0NDA3NTczLCJpYXQiOjE3ODg3ODgzNzMsImlzcyI6InN1cGFiYXNlIiwicHJvamVjdF9yZWYiOiJwNGMyNjE4YmY5M2NlNGEyZjQ1ZjgiLCJyb2xlIjoiYW5vbiJ9.u-E7X433Llwcg-5jF8IDiHwiHqaBN_xtjuvkuEA7Llo')"

content = re.sub(old_url, new_url, content)
content = re.sub(old_key, new_key, content)

with open('server.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("SERVER_REVERTED")
