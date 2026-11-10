import requests, json

s = requests.Session()
s.post('https://varantradarpro.pythonanywhere.com/login', json={'username': 'nebioglur', 'password': '123'})

r = s.get('https://varantradarpro.pythonanywhere.com/api/simulation/daily_pnl', timeout=20)
d = r.json()
trades = d.get('trades', [])
print(f"Total trades: {len(trades)}")
for t in trades:
    print(t.get('date_str'), t.get('symbol'), 'Entry:', t.get('entry_time'), t.get('entry_price'), 'Exit:', t.get('exit_time'), t.get('exit_price'), 'PnL:', t.get('pnl_pct'), 'Reason:', repr(t.get('exit_reason')))
