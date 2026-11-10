import json

with open('dashboard_cache.json', 'r', encoding='utf-8') as f:
    cache = json.load(f)

stats = cache.get('all_symbols_stats', {})
regime_data = cache.get('v8_market_regime', {})

print("Regime in cache:", regime_data.get('regime'))

# Check all symbols that have breakout or execution
candidates = []
for sym, data in stats.items():
    bo = data.get('v8_breakout') or {}
    ex = data.get('v8_execution') or {}
    disc = data.get('v8_discovery') or {}
    if bo.get('is_breakout') or ex.get('entry_status') == 'ENTER':
        candidates.append((sym, data))

print(f"Total candidate symbols with breakout or execution: {len(candidates)}")

for sym, data in candidates:
    bo = data.get('v8_breakout') or {}
    ex = data.get('v8_execution') or {}
    chg = data.get('Change_Pct', 0.0)
    vol = data.get('Volume', 0)
    vol_ratio = data.get('Volume_Ratio', 1.0)
    print(f"\n[{sym}]")
    print(f"  bo.is_breakout: {bo.get('is_breakout')}, score: {bo.get('breakout_score')}, fakeout: {bo.get('fakeout_risk')}")
    print(f"  ex.entry_status: {ex.get('entry_status')}, reasons: {ex.get('reasons')}")
    print(f"  Change_Pct: {chg}%, Volume: {vol}, VolRatio: {vol_ratio}")
