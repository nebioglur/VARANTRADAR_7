import requests

s = requests.Session()
s.post("https://varantradarpro.pythonanywhere.com/login", json={"username": "nebioglur", "password": "123"})
r = s.get("https://varantradarpro.pythonanywhere.com/api/v8/radar/breakout")
data = r.json().get("data", [])
print(f"Total breakout items: {len(data)}")

statuses = {}
for d in data:
    st = d.get("entry_status", "UNKNOWN")
    statuses[st] = statuses.get(st, 0) + 1

print("Status distribution:", statuses)

print("\nSample top 5 items:")
for d in data[:5]:
    print(f"- {d.get('symbol')}: status={d.get('entry_status')}, score={d.get('breakout_score')}, price={d.get('price')}, reasons={d.get('entry_reasons')}")
