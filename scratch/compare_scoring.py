import json

with open('scratch/verd_breakout.json', encoding='utf-8') as f:
    verd = json.load(f)

v_syms = [x['symbol'] for x in verd.get('data', [])]
print(f"Verdent count: {len(v_syms)}")

with open('dashboard_cache.json', encoding='utf-8') as f:
    dash = json.load(f)

all_stats = dash.get('all_symbols_stats', {})

# Check how many symbols in dashboard_cache have fallback_score >= 59.0
scores = []
for sym, data in all_stats.items():
    chg = float(data.get("Change_Pct") or 0)
    v = data.get("Volume", 0)
    av = data.get("Avg_Volume_10d", 0) or 0
    rel_vol = round(v / av, 2) if av > 0 else 1.0
    fallback_score = max(35.0, min(65.0, 48.0 + chg * 2.0 + (rel_vol - 1.0) * 5.0))
    scores.append((sym, chg, rel_vol, round(fallback_score, 1)))

scores.sort(key=lambda x: x[3], reverse=True)
print("Top 10 computed scores:")
for s in scores[:10]:
    print(s)

print(f"\nHow many symbols have score == 65.0? {len([s for s in scores if s[3] == 65.0])}")
print(f"How many symbols have score >= 59.0? {len([s for s in scores if s[3] >= 59.0])}")
