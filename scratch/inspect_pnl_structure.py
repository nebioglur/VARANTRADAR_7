import requests
import json

s = requests.Session()
s.post("https://varantradarpro.pythonanywhere.com/login", json={"username": "nebioglur", "password": "123"})
r = s.get("https://varantradarpro.pythonanywhere.com/api/simulation/daily_pnl")
data = r.json()
print("Top-level keys:", list(data.keys()))
for k in ["equity_curve", "trades", "performance", "weekly_summary", "weekly_target"]:
    v = data.get(k)
    print(f"\n--- {k} ---")
    if isinstance(v, list):
        print(f"List of {len(v)} items. First item: {v[0] if v else 'EMPTY'}")
    elif isinstance(v, dict):
        print(json.dumps(v, indent=2))
    else:
        print(v)
