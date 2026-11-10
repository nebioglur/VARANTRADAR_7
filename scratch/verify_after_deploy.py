import requests
import time

BASE_URL = "https://varantradarpro.pythonanywhere.com"
s = requests.Session()
s.headers.update({"User-Agent": "AuditBot/2.0"})

time.sleep(3) # Wait for wsgi reload

# 1. Login
r_log = s.post(f"{BASE_URL}/login", json={"username": "nebioglur", "password": "123"}, timeout=15)
print("[1] Login Status:", r_log.status_code, r_log.json())

# 2. Telegram Buttons
print("\n[2] Testing Telegram Endpoints:")
r_test = s.post(f"{BASE_URL}/api/telegram/test", timeout=15)
print(f"  Test Message: {r_test.status_code} | {r_test.text}")

r_compass = s.post(f"{BASE_URL}/api/telegram/send_morning_compass", timeout=15)
print(f"  Morning Compass: {r_compass.status_code} | {r_compass.text}")

r_tavan = s.post(f"{BASE_URL}/api/telegram/send_tavan_candidates", timeout=15)
print(f"  Tavan Candidates: {r_tavan.status_code} | {r_tavan.text}")

r_special = s.post(f"{BASE_URL}/api/telegram/send_special_ranking", timeout=15)
print(f"  Special Ranking: {r_special.status_code} | {r_special.text}")

# 3. Simulation Daily PnL
print("\n[3] Simulation Daily PnL Fields:")
r_pnl = s.get(f"{BASE_URL}/api/simulation/daily_pnl", timeout=15)
pnl = r_pnl.json()
print("  status:", pnl.get("status"))
print("  initial_balance:", pnl.get("initial_balance"))
print("  current_balance:", pnl.get("current_balance"))
print("  cumulative_balance:", pnl.get("cumulative_balance"))
print("  net_pnl:", pnl.get("net_pnl"))
print("  win_rate:", pnl.get("win_rate"))
print("  total_trades:", pnl.get("total_trades"))

# 4. APK Endpoints
print("\n[4] APK Endpoints:")
r_apk1 = s.get(f"{BASE_URL}/apk/VarantRadarPro.apk", timeout=15)
print(f"  /apk/VarantRadarPro.apk: {r_apk1.status_code} | Length: {len(r_apk1.content)} | Type: {r_apk1.headers.get('Content-Type')}")

r_apk2 = s.get(f"{BASE_URL}/ui/apk/VarantRadarPro.apk", timeout=15)
print(f"  /ui/apk/VarantRadarPro.apk: {r_apk2.status_code} | Length: {len(r_apk2.content)} | Type: {r_apk2.headers.get('Content-Type')}")
