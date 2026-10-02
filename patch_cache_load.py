# -*- coding: utf-8 -*-
with open('server.py', 'r', encoding='utf-8') as f:
    text = f.read()

import re

# Fix load_dashboard_cache to ignore old dates entirely!
pattern = r'def load_dashboard_cache\(\).*?return data\n.*?except Exception.*?return \{\}'
replacement = r'''def load_dashboard_cache():
    import os, json
    from datetime import datetime
    try:
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                today_str = datetime.now().strftime("%Y-%m-%d")
                if data.get("cache_date") != today_str:
                    return {} # DONT LOAD YESTERDAY'S DATA!
                return data
    except Exception:
        pass
    return {}'''

text = re.sub(pattern, replacement, text, flags=re.DOTALL)

with open('server.py', 'w', encoding='utf-8') as f:
    f.write(text)
print("LOAD CACHE PATCH OK")
