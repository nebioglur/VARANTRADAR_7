import urllib.request
import json
import time

BASE_URL = "https://varantradarpro.pythonanywhere.com"
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor())

def test_ep(name, path, method="GET", data=None):
    try:
        url = f"{BASE_URL}{path}"
        req_data = None
        headers = {"User-Agent": "AuditBot/1.0"}
        if data is not None:
            if isinstance(data, dict):
                req_data = json.dumps(data).encode('utf-8')
                headers["Content-Type"] = "application/json"
            elif isinstance(data, str):
                req_data = data.encode('utf-8')
                headers["Content-Type"] = "application/x-www-form-urlencoded"
        req = urllib.request.Request(url, data=req_data, headers=headers, method=method)
        t0 = time.time()
        with opener.open(req, timeout=20) as r:
            duration = round((time.time() - t0) * 1000)
            status = r.status
            content_type = r.headers.get("Content-Type", "")
            raw = r.read()
            if "application/json" in content_type:
                res = json.loads(raw.decode('utf-8'))
                print(f"[OK] {name} ({method} {path}) -> {status} in {duration}ms | Keys: {list(res.keys())[:6]}")
                return res
            else:
                print(f"[OK] {name} ({method} {path}) -> {status} in {duration}ms | Length: {len(raw)} bytes ({content_type})")
                return raw
    except Exception as e:
        print(f"[ERR] {name} ({method} {path}) -> Error: {e}")
        return None

print("=== 1. LOGIN ===")
test_ep("Login", "/login", "POST", "username=nebioglur&password=123")

print("\n=== 2. CORE DASHBOARD & MARKET ===")
test_ep("Dashboard Init", f"/api/dashboard_init?t={int(time.time()*1000)}")

print("\n=== 3. V8 SUITE ===")
test_ep("V8 Market Regime", "/api/v8/market/regime")
test_ep("V8 Playbook", "/api/v8/playbook")
test_ep("V8 Weekly", "/api/v8/weekly")
test_ep("V8 Discovery", "/api/v8/radar/discovery")
test_ep("V8 Entry Approval", "/api/v8/entry-approval")
test_ep("V8 KAP Status", "/api/v8/kap/status")

print("\n=== 4. SIMULATION & TRADE LOG ===")
test_ep("Simulation Terminal", "/api/simulation/terminal")
test_ep("Simulation Daily PnL", "/api/simulation/daily_pnl")
test_ep("Admin Simulation Run", "/api/admin/simulation/run", "POST", {})

print("\n=== 5. TELEGRAM ===")
test_ep("Telegram Settings", "/api/telegram/settings")
test_ep("Telegram Test Suite", "/api/telegram/test_suite")

print("\n=== 6. APK ARTIFACT ===")
test_ep("APK Download", "/apk/VarantRadarPro.apk")
test_ep("UI APK Download", "/ui/apk/VarantRadarPro.apk")
