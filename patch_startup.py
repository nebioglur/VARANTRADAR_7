# -*- coding: utf-8 -*-
with open('server.py', 'r', encoding='utf-8') as f:
    text = f.read()

import re

# Fix cache clearing logic on startup
pattern_cache = r'(def api_dashboard_init\(\):.*?clean_cache = sanitize_for_json\(GLOBAL_DASHBOARD_CACHE\))'
replacement_cache = r'''def api_dashboard_init():
    from datetime import datetime
    today_str = datetime.now().strftime("%Y-%m-%d")
    global GLOBAL_DASHBOARD_CACHE
    if GLOBAL_DASHBOARD_CACHE and GLOBAL_DASHBOARD_CACHE.get("cache_date") != today_str:
        GLOBAL_DASHBOARD_CACHE = {} # CLEAR STALE CACHE

    try:
        start_live_data_collector()
    except Exception:
        pass
    clean_cache = sanitize_for_json(GLOBAL_DASHBOARD_CACHE)'''

text = re.sub(r'def api_dashboard_init\(\):.*?clean_cache = sanitize_for_json\(GLOBAL_DASHBOARD_CACHE\)', replacement_cache, text, flags=re.DOTALL)

with open('server.py', 'w', encoding='utf-8') as f:
    f.write(text)
print("STARTUP CACHE PATCH OK")
