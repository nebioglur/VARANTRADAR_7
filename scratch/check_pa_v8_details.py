import requests

s = requests.Session()
s.post("https://varantradarpro.pythonanywhere.com/login", json={"username": "nebioglur", "password": "123"}, timeout=15)
r = s.get("https://varantradarpro.pythonanywhere.com/api/dashboard_init", timeout=15)
d = r.json()

cache_date = d.get("cache_date")
last_updated = d.get("last_updated")
data_fresh = d.get("data_fresh")
market = d.get("market")
stats = d.get("dashboard_data", {}).get("all_symbols_stats", {})

print(f"cache_date: {cache_date}")
print(f"last_updated: {last_updated}")
print(f"data_fresh: {data_fresh}")
print(f"market: {market}")
print(f"Total symbols: {len(stats)}")

for sym in ["THYAO.IS", "GARAN.IS", "ASELS.IS", "ADGYO.IS", "BIOEN.IS"]:
    sd = stats.get(sym, {})
    print(f"\n--- {sym} ---")
    print(f"Price: {sd.get('Price')}, Change_Pct: {sd.get('Change_Pct')}, Volume: {sd.get('Volume')}")
    print(f"v8_breakout: {sd.get('v8_breakout')}")
    print(f"v8_execution: {sd.get('v8_execution')}")
    print(f"v8_discovery: {sd.get('v8_discovery')}")
