import json

with open('dashboard_cache.json', encoding='utf-8') as f:
    dash = json.load(f)

all_stats = dash.get("all_symbols_stats", {})
keys = list(all_stats.keys())
print("Are all_stats keys alphabetically sorted?", keys == sorted(keys))
print("First 10 keys:", keys[:10])
