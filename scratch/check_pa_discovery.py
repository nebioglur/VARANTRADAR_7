import requests

s = requests.Session()
s.post("https://varantradarpro.pythonanywhere.com/login", json={"username": "nebioglur", "password": "123"}, timeout=15)
r = s.get("https://varantradarpro.pythonanywhere.com/api/v8/radar/discovery", timeout=15)
data = r.json().get("data", [])
print(f"Total discovery: {len(data)}")

states = {}
for d in data:
    st = d.get("state")
    states[st] = states.get(st, 0) + 1
print("Discovery states:", states)

for d in data[:5]:
    print(f"- {d.get('symbol')}: state={d.get('state')}, score={d.get('preparation_score')}, reasons={d.get('reasons')}")
