import requests
import json

s = requests.Session()
# Login with nebioglur / 123
login_res = s.post('https://varantradarpro.pythonanywhere.com/login', json={'username': 'nebioglur', 'password': '123'}, timeout=15)
print("Login status:", login_res.status_code)

# 1. Check V8 Radar Breakout
r_v8 = s.get('https://varantradarpro.pythonanywhere.com/api/v8/radar/breakout', timeout=20)
print("V8 breakout status:", r_v8.status_code)
if r_v8.status_code == 200:
    v8_json = r_v8.json()
    items = v8_json.get('data', [])
    from collections import Counter
    counts = Counter(x.get('entry_status') for x in items)
    print("V8 Counts:", counts)
    waits = [x.get('symbol') for x in items if x.get('entry_status') == 'WAIT']
    print("WAIT symbols (BEKLE):", waits)

# 2. Check V8 Weekly
r_wk = s.get('https://varantradarpro.pythonanywhere.com/api/v8/weekly', timeout=20)
print("\nV8 weekly status:", r_wk.status_code)
if r_wk.status_code == 200:
    wk_json = r_wk.json()
    print("Weekly week_pnl:", wk_json.get('week_pnl'))
    print("Weekly week_pct:", wk_json.get('week_pct'))
    print("Weekly trades_count:", wk_json.get('trades_count'))
    print("Weekly wins/losses:", f"{wk_json.get('wins')}K / {wk_json.get('losses')}Z")
    print("Weekly remaining_pct:", wk_json.get('remaining_pct'))

# 3. Check Simulation daily_pnl
r_sim = s.get('https://varantradarpro.pythonanywhere.com/api/simulation/daily_pnl', timeout=20)
print("\nSimulation daily_pnl status:", r_sim.status_code)
if r_sim.status_code == 200:
    sim_json = r_sim.json()
    print("Sim current_balance:", sim_json.get('current_balance'))
    print("Sim net_pnl:", sim_json.get('net_pnl'))
    trades = sim_json.get('trades', [])
    print(f"Sim trades count: {len(trades)}")
    for t in trades:
        print(f"  {t.get('symbol')} | {t.get('date_str')} | pnl: {t.get('pnl_val')} | pnl_pct: {t.get('pnl_pct')}%")
    eq_curve = sim_json.get('equity_curve', [])
    print(f"Equity curve points: {len(eq_curve)}")
    for eq in eq_curve:
        print(f"  {eq.get('date_str')} -> end: {eq.get('end_equity')} | daily: {eq.get('daily_pnl')}")
