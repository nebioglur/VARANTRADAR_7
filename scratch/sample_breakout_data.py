import requests

s = requests.Session()
s.post('https://varantradarpro.pythonanywhere.com/login', json={'username': 'nebioglur', 'password': '123'}, timeout=15)
r = s.get('https://varantradarpro.pythonanywhere.com/api/v8/radar/breakout', timeout=15)
data = r.json().get('data', [])

print("Sample items with scores and reasons:")
for d in data[:15]:
    sym = d.get('symbol')
    st = d.get('entry_status')
    sc = d.get('breakout_score')
    pr = d.get('price')
    ch = d.get('change_pct')
    reasons = d.get('entry_reasons', [])
    print(f"{sym:10} | status={st:12} | score={sc} | price={pr} | chg={ch}% | reasons={reasons[:2]}")
