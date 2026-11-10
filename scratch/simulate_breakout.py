import json

with open('dashboard_cache.json', 'r', encoding='utf-8') as f:
    d = json.load(f)

all_stats = d.get('all_symbols_stats', {})

bo_count = 0
disc_count = 0
fallback_count = 0

for sym, data in all_stats.items():
    if data.get("Price_Stale") and not data.get("v8_breakout", {}).get("is_breakout"):
        continue
    bo = data.get("v8_breakout")
    if bo and bo.get("is_breakout"):
        bo_count += 1
        continue
    intra = data.get("v8_breakout_1h") or {}
    intra_bo = intra.get("breakout") or {}
    if intra_bo.get("is_breakout") and intra.get("entry_status") == "ENTER":
        bo_count += 1
        continue
    disc = data.get("v8_discovery") or {}
    state = disc.get("state")
    if state in ("READY", "PREPARING", "WATCH"):
        disc_count += 1
        continue
    if data.get("Daily_Close") or data.get("Price"):
        fallback_count += 1

print(f"bo_count: {bo_count}")
print(f"disc_count: {disc_count}")
print(f"fallback_count: {fallback_count}")
