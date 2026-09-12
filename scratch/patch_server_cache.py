import os

with open('server.py', 'r', encoding='utf-8') as f:
    text = f.read()

import re
# Find where today_str is assigned
match = re.search(r'today_str = datetime\.now\(\)\.strftime\("%Y-%m-%d"\)', text)
if match:
    idx = match.end()
    insertion = """
            if GLOBAL_DASHBOARD_CACHE.get("cache_date", today_str) != today_str:
                print("[BACKGROUND] Yeni gun tespit edildi. Eski bellekteki veriler temizleniyor.")
                GLOBAL_DASHBOARD_CACHE = {}
"""
    if 'Yeni gun tespit' not in text[idx:idx+300]:
        new_text = text[:idx] + insertion + text[idx:]
        with open('server.py', 'w', encoding='utf-8') as f:
            f.write(new_text)
        print("Inserted cache clearer")
    else:
        print("Already present")
else:
    print("Could not find today_str assignment")
