import json

with open('dashboard_cache.json', 'r', encoding='utf-8') as f:
    cache = json.load(f)

all_stats = cache.get("all_symbols_stats", {})

# Let's inspect the symbols in scratch/verd_breakout.json
with open('scratch/verd_breakout.json', 'r', encoding='utf-8') as f:
    verd = json.load(f)

v_syms = [x['symbol'] for x in verd.get('data', [])]
print("Verdent symbols count:", len(v_syms))

# How many symbols in all_stats are in v_syms?
missing = [s for s in v_syms if s not in all_stats]
print("Missing from all_stats:", missing)

# Now check the 10 WAIT symbols from Verdent
waits = [x['symbol'] for x in verd.get('data', []) if x['entry_status'] == 'WAIT']
print("Verdent WAIT symbols:", waits)

for s in waits:
    data = all_stats.get(s, {})
    chg = float(data.get("Change_Pct") or 0)
    v = data.get("Volume", 0)
    av = data.get("Avg_Volume_10d", 0) or 0
    rel_vol = round(v / av, 2) if av > 0 else 1.0
    fallback_score = max(35.0, min(65.0, 48.0 + chg * 2.0 + (rel_vol - 1.0) * 5.0))
    print(f"{s:8s} | chg: {chg:5.2f}% | rel_vol: {rel_vol:4.2f} | score: {fallback_score:5.1f}")
