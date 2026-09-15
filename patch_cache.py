# -*- coding: utf-8 -*-
with open('server.py', 'r', encoding='utf-8') as f:
    content = f.read()

import re

old_code = r'''def load_dashboard_cache\(\):
    try:
        if os\.path\.exists\("data/dashboard_cache\.json"\):
            with open\("data/dashboard_cache\.json", "r", encoding="utf-8"\) as f:
                return json\.load\(f\)
    except Exception as e:
        print\(f"Cache load error: \{e\}"\)
    return \{\}

def save_dashboard_cache\(data\):
    try:
        os\.makedirs\("data", exist_ok=True\)
        with open\("data/dashboard_cache\.json", "w", encoding="utf-8"\) as f:
            json\.dump\(data, f, ensure_ascii=False\)
    except Exception as e:
        print\(f"Cache save error: \{e\}"\)'''

new_code = '''IN_MEMORY_DASHBOARD_CACHE = {}

def load_dashboard_cache():
    global IN_MEMORY_DASHBOARD_CACHE
    try:
        from services.supabase_client import get_kv
        sb_cache = get_kv("dashboard_cache", "global_cache", None)
        if sb_cache:
            IN_MEMORY_DASHBOARD_CACHE = sb_cache
            return sb_cache
    except Exception as e:
        print(f"[Supabase] Cache okuma hatasi: {e}")
    return IN_MEMORY_DASHBOARD_CACHE

def save_dashboard_cache(data):
    global IN_MEMORY_DASHBOARD_CACHE
    IN_MEMORY_DASHBOARD_CACHE = data
    try:
        from services.supabase_client import set_kv
        set_kv("dashboard_cache", "global_cache", data)
    except Exception as e:
        print(f"[Supabase] Cache yazma hatasi: {e}")'''

content = re.sub(old_code, new_code, content)
with open('server.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("PATCH_CACHE_OK")
