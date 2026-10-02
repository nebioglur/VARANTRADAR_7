# -*- coding: utf-8 -*-
from server import GLOBAL_DASHBOARD_CACHE, load_dashboard_cache
cache = load_dashboard_cache()
print("Keys in load_dashboard_cache:", list(cache.keys()))
print("all_symbols_stats len:", len(cache.get('all_symbols_stats', {})))

print("Keys in GLOBAL:", list(GLOBAL_DASHBOARD_CACHE.keys()) if GLOBAL_DASHBOARD_CACHE else 'None')
if GLOBAL_DASHBOARD_CACHE:
    print("GLOBAL all_symbols_stats len:", len(GLOBAL_DASHBOARD_CACHE.get('all_symbols_stats', {})))
