import urllib.request, json, http.cookiejar

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

# Login
login_data = json.dumps({"username": "nebioglur", "password": "123"}).encode('utf-8')
opener.open(urllib.request.Request("https://varantradarpro.pythonanywhere.com/login", data=login_data, headers={"Content-Type": "application/json"}))

resp = opener.open(urllib.request.Request("https://varantradarpro.pythonanywhere.com/api/simulation/daily_pnl"))
d = json.loads(resp.read().decode())
print("Equity curve points:", d.get("equity_curve"))
