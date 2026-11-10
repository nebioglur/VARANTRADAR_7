import json

with open('dashboard_cache.json', 'r', encoding='utf-8') as f:
    d = json.load(f)

print("dashboard_cache.json keys:", list(d.keys())[:10])
stats = d.get("all_symbols_stats", {})
print("Total symbols in stats:", len(stats))

has_v8_bo = 0
has_v8_bo_true = 0
has_v8_exec = 0
has_v8_exec_enter = 0
has_v8_disc = 0
has_v8_1h = 0
has_v8_1h_enter = 0

for sym, data in stats.items():
    if not isinstance(data, dict): continue
    if data.get("v8_breakout"):
        has_v8_bo += 1
        if data["v8_breakout"].get("is_breakout"):
            has_v8_bo_true += 1
    if data.get("v8_execution"):
        has_v8_exec += 1
        if data["v8_execution"].get("entry_status") == "ENTER":
            has_v8_exec_enter += 1
    if data.get("v8_discovery"):
        has_v8_disc += 1
    if data.get("v8_breakout_1h"):
        has_v8_1h += 1
        if data["v8_breakout_1h"].get("entry_status") == "ENTER":
            has_v8_1h_enter += 1

print(f"v8_breakout: {has_v8_bo}, is_breakout=True: {has_v8_bo_true}")
print(f"v8_execution: {has_v8_exec}, entry_status=ENTER: {has_v8_exec_enter}")
print(f"v8_discovery: {has_v8_disc}")
print(f"v8_breakout_1h: {has_v8_1h}, 1h entry_status=ENTER: {has_v8_1h_enter}")
