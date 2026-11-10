import urllib.request, urllib.parse, http.cookiejar, json

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

# Login
login_data = json.dumps({"username": "nebioglur", "password": "123"}).encode('utf-8')
req = urllib.request.Request("https://varantradarpro.pythonanywhere.com/login", data=login_data, headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"})
with opener.open(req, timeout=15) as resp:
    pass

for ep in ['/api/v8/playbook', '/api/v8/weekly', '/api/v8/market/regime']:
    url = f"https://varantradarpro.pythonanywhere.com{ep}"
    try:
        with opener.open(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=15) as resp:
            data = json.loads(resp.read().decode())
            print(f"{ep}: status={data.get('status')}")
    except Exception as e:
        print(f"{ep} error: {e}")
