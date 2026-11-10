import urllib.request, urllib.parse, http.cookiejar, json

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

# 1. Login
login_data = json.dumps({"username": "nebioglur", "password": "123"}).encode('utf-8')
req = urllib.request.Request("https://varantradarpro.pythonanywhere.com/login", data=login_data, headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"})
with opener.open(req, timeout=15) as resp:
    pass

# 2. Check Simulation daily_pnl
url = 'https://varantradarpro.pythonanywhere.com/api/simulation/daily_pnl'
with opener.open(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=15) as resp:
    data = json.loads(resp.read().decode())
    print("performance:", json.dumps(data.get("performance"), indent=2))
    print("weekly_target:", json.dumps(data.get("weekly_target"), indent=2))
    print("weekly_summary:", json.dumps(data.get("weekly_summary"), indent=2))
