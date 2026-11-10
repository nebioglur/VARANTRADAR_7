import requests
import json

s = requests.Session()
s.post("https://varantradarpro.pythonanywhere.com/login", json={"username": "nebioglur", "password": "123"})

for ep in [
    "/api/v8/market/regime",
    "/api/v8/playbook",
    "/api/v8/weekly",
    "/api/v8/radar/discovery",
    "/api/v8/entry-approval",
    "/api/v8/radar/breakout"
]:
    r = s.get(f"https://varantradarpro.pythonanywhere.com{ep}")
    print(f"=== {ep} (Status {r.status_code}) ===")
    try:
        d = r.json()
        for k, v in d.items():
            if isinstance(v, list):
                print(f"  {k}: list of {len(v)} items")
                if v:
                    print(f"    first: {v[0]}")
            elif isinstance(v, dict):
                print(f"  {k}: dict with keys {list(v.keys())[:6]}")
            else:
                print(f"  {k}: {v}")
    except Exception as e:
        print(f"  Error parsing json: {e} | Text: {r.text[:200]}")
