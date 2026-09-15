# -*- coding: utf-8 -*-
import os

with open('server.py', 'r', encoding='utf-8') as f:
    content = f.read()

import re

# Auth Config guncellemesi
old_auth = '''@app.route('/api/auth_config')
def get_auth_config():
    return jsonify({
        "url": os.environ.get("SUPABASE_URL", ""),
        "key": os.environ.get("SUPABASE_PUBLISHABLE_KEY", "")
    })'''

new_auth = '''@app.route('/api/auth_config')
def get_auth_config():
    return jsonify({
        "url": os.environ.get("SUPABASE_URL", "https://kfslwkmrnjqxirzhfmbn.supabase.co"),
        "key": os.environ.get("SUPABASE_PUBLISHABLE_KEY", "sb_publishable_RP_ouZJiDHK_PA_3o1dmfg_G5BgAuzl")
    })'''

content = content.replace(old_auth, new_auth)
with open('server.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("PATCH_AUTH_CONFIG_OK")
