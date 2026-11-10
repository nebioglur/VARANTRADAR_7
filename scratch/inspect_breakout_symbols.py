import json

with open('dashboard_cache.json', 'r', encoding='utf-8') as f:
    d = json.load(f)

stats = d.get("all_symbols_stats", {})
for sym, data in stats.items():
    if not isinstance(data, dict): continue
    bo = data.get("v8_breakout") or {}
    if bo.get("is_breakout"):
        print(f"\n=== {sym} ===")
        print(f"Price: {data.get('Price')}, Change_Pct: {data.get('Change_Pct')}, Volume: {data.get('Volume')}")
        print("v8_breakout:", bo)
        print("v8_execution:", data.get("v8_execution"))
        print("v8_breakout_1h:", data.get("v8_breakout_1h"))
