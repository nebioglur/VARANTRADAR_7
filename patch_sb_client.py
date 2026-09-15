# -*- coding: utf-8 -*-
import os

with open('services/supabase_client.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_client = '''SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_PUBLISHABLE_KEY", "")'''

new_client = '''SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://kfslwkmrnjqxirzhfmbn.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_PUBLISHABLE_KEY", "sb_publishable_RP_ouZJiDHK_PA_3o1dmfg_G5BgAuzl")'''

content = content.replace(old_client, new_client)
with open('services/supabase_client.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("PATCH_SB_CLIENT_OK")
