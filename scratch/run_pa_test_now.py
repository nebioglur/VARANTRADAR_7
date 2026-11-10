import urllib.request, json, http.cookiejar

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

# Login
login_data = json.dumps({"username": "nebioglur", "password": "123"}).encode('utf-8')
opener.open(urllib.request.Request("https://varantradarpro.pythonanywhere.com/login", data=login_data, headers={"Content-Type": "application/json"}))

# Trigger for 2026-11-05
req = urllib.request.Request(
    "https://varantradarpro.pythonanywhere.com/api/admin/simulation/run",
    data=json.dumps({"date": "2026-11-05"}).encode('utf-8'),
    headers={"Content-Type": "application/json"}
)
try:
    with opener.open(req, timeout=60) as resp:
        print("Admin sim run 2026-11-05:", json.loads(resp.read().decode()))
except Exception as e:
    print("Admin sim run 2026-11-05 error:", e)

# Check daily_pnl
try:
    with opener.open(urllib.request.Request("https://varantradarpro.pythonanywhere.com/api/simulation/daily_pnl"), timeout=20) as resp:
        data = json.loads(resp.read().decode())
        print("Trades count:", len(data.get("trades", [])))
        for t in data.get("trades", [])[:5]:
            print("Trade:", t.get('symbol'), t.get('entry_time'), t.get('pnl_pct'), t.get('exit_reason'))
except Exception as e:
    print("daily_pnl error:", e)
