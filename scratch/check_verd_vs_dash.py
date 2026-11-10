import json

with open('scratch/verd_breakout.json', encoding='utf-8') as f:
    verd = json.load(f)

v_syms = set(x['symbol'] for x in verd.get('data', []))

with open('dashboard_cache.json', encoding='utf-8') as f:
    dash = json.load(f)

stats = dash.get('all_symbols_stats', {})

bo_syms = [s for s, d in stats.items() if d.get('v8_breakout', {}).get('is_breakout')]
print("Symbols in dashboard_cache with v8_breakout.is_breakout:", len(bo_syms))
print(bo_syms)

print("\nAre all bo_syms in Verdent?")
for s in bo_syms:
    print(s, "in Verdent?", s in v_syms)
