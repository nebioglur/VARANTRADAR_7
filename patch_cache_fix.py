# -*- coding: utf-8 -*-
with open('server.py', 'r', encoding='utf-8') as f:
    content = f.read()

import re

# 1. 30 dakika kuralini ve "Eski gun reddedildi" kurallarini sil
# def load_dashboard_cache() icindeki if cache_date and cache_date != today_str: kisimlari
new_cache_logic = '''
def load_dashboard_cache():
    if os.path.exists(CACHE_FILE):
        try:
            import json
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data
        except Exception as e:
            print(f"Cache load error: {e}")
    return {}
'''
content = re.sub(r'def load_dashboard_cache\(\):.*?return \{\}\n', new_cache_logic, content, flags=re.DOTALL)

# 2. Render'da agir taramayi iptal et (Masaustunde calissin)
# _background_scanner_impl'in basina kontrol koyalim
new_bg = '''def _background_scanner_impl():
    import os
    if os.environ.get("RENDER"):
        print("[BACKGROUND] Render sunucusunda agir BIST taramasi IP iptali yuzunden kapatildi. Cache'den devam edilecek.")
        return
'''
content = content.replace("def _background_scanner_impl():", new_bg)

with open('server.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("PATCH_CACHE_OK")
