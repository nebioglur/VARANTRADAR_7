import json

with open('dashboard_cache.json', 'r', encoding='utf-8') as f:
    cache = json.load(f)

stats = cache.get('all_symbols_stats', {})
candidates = []
for sym, d in stats.items():
    if not isinstance(d, dict): continue
    price = float(d.get('Price') or d.get('Daily_Close') or 0)
    ch = float(d.get('Change_Pct') or 0)
    vol = float(d.get('Vol_Multiplier') or d.get('Volume_Ratio') or 0)
    vol_tl = float(d.get('Volume_TL') or (float(d.get('Volume', 0)) * price) or 0)
    score = float(d.get('Score', 0) or d.get('score', 0))
    
    if price >= 4.0 and 0.5 <= ch < 5.0 and vol >= 1.2 and vol_tl >= 25_000_000:
        candidates.append((sym, price, ch, vol, score))

print(f"Qualified momentum candidates in cache: {len(candidates)}")
for c in candidates[:15]:
    print("  Candidate:", c[0], f"Price: {c[1]}", f"Ch: %{c[2]:.2f}", f"Vol: {c[3]:.1f}x", f"Score: {c[4]}")
