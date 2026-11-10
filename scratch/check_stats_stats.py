import json

with open('dashboard_cache.json', 'r', encoding='utf-8') as f:
    cache = json.load(f)

for k in ['opportunities', 'gainers', 'opportunities_1h', 'tavan_adaylari']:
    items = cache.get(k, [])
    print(f"{k}: {len(items)} items")

stats = cache.get('all_symbols_stats', {})
print(f"all_symbols_stats: {len(stats)} symbols")

# Let's count how many have positive change and high score
pos_stocks = []
for sym, d in stats.items():
    if isinstance(d, dict) and (float(d.get('Change_Pct') or 0) > 0.5):
        pos_stocks.append(sym)
print(f"Positive stocks (>0.5%): {len(pos_stocks)}")
