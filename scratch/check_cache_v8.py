import json

with open('dashboard_cache.json', 'r', encoding='utf-8') as f:
    d = json.load(f)

stats = d.get('all_symbols_stats', {})
print("Total symbols in dashboard_cache:", len(stats))
for sym in ['FZLGY.IS', 'GARAN.IS', 'YUNSA.IS', 'FROTO.IS']:
    s = stats.get(sym, {})
    bo = s.get('v8_breakout')
    exe = s.get('v8_execution')
    print(f"\n--- {sym} ---")
    print("v8_breakout:", bo)
    print("v8_execution:", exe)
