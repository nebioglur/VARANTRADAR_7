import json

with open('scratch/verd_breakout.json', encoding='utf-8') as f:
    verd = json.load(f)

with open('dashboard_cache.json', encoding='utf-8') as f:
    dash = json.load(f)

stats = dash.get('all_symbols_stats', {})

verd_waits = [x for x in verd.get('data', []) if x.get('entry_status') == 'WAIT']

print("Verdent WAIT items count:", len(verd_waits))
for item in verd_waits:
    sym = item.get('symbol')
    s = stats.get(sym, {})
    print(f"\nSymbol: {sym}")
    print(f"  Verdent status: {item.get('status')}, score: {item.get('breakout_score')}, reasons: {item.get('entry_reasons')}")
    print(f"  Dash v8_discovery state: {s.get('v8_discovery', {}).get('state')}")
    print(f"  Dash v8_breakout is_bo: {s.get('v8_breakout', {}).get('is_breakout')}")
