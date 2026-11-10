import requests
import json
import time

BASE_URL = "https://varantradarpro.pythonanywhere.com"

s = requests.Session()
s.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})

print("=" * 60)
print("SYSTEM COMPREHENSIVE AUDIT REPORT")
print("Target:", BASE_URL)
print("Time:", time.strftime("%Y-%m-%d %H:%M:%S"))
print("=" * 60)

# 1. Login
print("\n[1] AUTHENTICATION")
r_login = s.post(f"{BASE_URL}/login", json={"username": "nebioglur", "password": "123"}, timeout=15)
print(f"POST /login -> Status {r_login.status_code}")
try:
    print("Response:", r_login.json())
except:
    print("Response text:", r_login.text[:100])

r_me = s.get(f"{BASE_URL}/api/me", timeout=15)
print(f"GET /api/me -> Status {r_me.status_code}, User: {r_me.json()}")

# 2. Dashboard Init
print("\n[2] DASHBOARD INIT & MARKET STATUS")
r_dash = s.get(f"{BASE_URL}/api/dashboard_init?t={int(time.time()*1000)}", timeout=15)
dash_data = r_dash.json()
m = dash_data.get('market', {})
print(f"Market Open: {m.get('is_open')} | Label: {m.get('label')} | Local Time: {m.get('local_time')}")
print(f"Data Fresh: {dash_data.get('data_fresh')} | Stale Suppressed: {dash_data.get('stale_data_suppressed')}")
print(f"Total Analyzed: {dash_data.get('total_analyzed')}")
all_syms = dash_data.get('dashboard_data', {}).get('all_symbols_stats', {})
tavan = dash_data.get('dashboard_data', {}).get('tavan_adaylari', [])
print(f"All Symbols Count: {len(all_syms)}")
print(f"Tavan Adaylari Count: {len(tavan)}")
if tavan:
    top3 = [f"{t.get('symbol')} ({t.get('change_str', t.get('last_price'))})" for t in tavan[:3]]
    print(f"Sample Tavan: {', '.join(top3)}")

# 3. V8 Engine
print("\n[3] V8 ENGINE & RADAR")
r_regime = s.get(f"{BASE_URL}/api/v8/market/regime", timeout=15)
print(f"GET /api/v8/market/regime -> {r_regime.status_code} | {r_regime.json()}")

r_pb = s.get(f"{BASE_URL}/api/v8/playbook", timeout=15)
pb = r_pb.json()
print(f"GET /api/v8/playbook -> Scenario: {pb.get('scenario', {}).get('label')}, Risk: %{pb.get('scenario', {}).get('risk_pct')}, Sectors: {len(pb.get('sector_pulse', []))}")

r_wk = s.get(f"{BASE_URL}/api/v8/weekly", timeout=15)
wk = r_wk.json()
print(f"GET /api/v8/weekly -> Target: %{wk.get('weekly', {}).get('target_pct')}, Realized: %{wk.get('weekly', {}).get('realized_pct')}")

r_disc = s.get(f"{BASE_URL}/api/v8/radar/discovery", timeout=15)
disc = r_disc.json()
print(f"GET /api/v8/radar/discovery -> Candidates: {len(disc.get('candidates', []))}")

# 4. Simulation & Trade Log
print("\n[4] SIMULATION & TRADE LOG")
r_term = s.get(f"{BASE_URL}/api/simulation/terminal", timeout=15)
print(f"GET /api/simulation/terminal -> Status {r_term.status_code} | Keys: {list(r_term.json().keys()) if r_term.status_code == 200 else r_term.text[:100]}")

r_pnl = s.get(f"{BASE_URL}/api/simulation/daily_pnl", timeout=15)
pnl = r_pnl.json()
print(f"GET /api/simulation/daily_pnl -> Status {r_pnl.status_code}")
print(f"  Trades count: {len(pnl.get('trades', []))}")
print(f"  Initial Balance: {pnl.get('initial_balance')}")
print(f"  Current Balance: {pnl.get('current_balance')}")
print(f"  Cumulative Balance: {pnl.get('cumulative_balance')}")
print(f"  Win Rate: {pnl.get('win_rate')}%")

# 5. Telegram
print("\n[5] TELEGRAM INTEGRATION")
r_tg = s.get(f"{BASE_URL}/api/telegram/settings", timeout=15)
print(f"GET /api/telegram/settings -> {r_tg.json()}")

# 6. APK Download
print("\n[6] APK DOWNLOAD")
r_apk = s.get(f"{BASE_URL}/apk/VarantRadarPro.apk", timeout=15)
print(f"GET /apk/VarantRadarPro.apk -> Status {r_apk.status_code}, Length: {len(r_apk.content)} bytes, Type: {r_apk.headers.get('Content-Type')}")

print("\n" + "=" * 60)
print("AUDIT COMPLETED")
print("=" * 60)
