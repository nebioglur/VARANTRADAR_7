import urllib.request, urllib.parse, http.cookiejar, json

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

# 1. Login
login_data = json.dumps({"username": "nebioglur", "password": "123"}).encode('utf-8')
req = urllib.request.Request("https://varantradarpro.pythonanywhere.com/login", data=login_data, headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"})
try:
    with opener.open(req, timeout=15) as resp:
        print("Login status:", json.loads(resp.read().decode()))
except Exception as e:
    print("Login error:", e)

# 2. Check Backtest
try:
    url = 'https://varantradarpro.pythonanywhere.com/api/backtest/run?symbol=THYAO&strategy=MACD_RSI_CROSS&capital=10000&period=1y&interval=1d&trailing_stop=0&stop_loss=0'
    with opener.open(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=25) as resp:
        data = json.loads(resp.read().decode())
        print("Live Backtest:", data.get("status"), "Trades count:", len(data.get("backtest", {}).get("trades", [])))
except Exception as e:
    print("Live Backtest error:", e)

# 3. Check Simulation daily_pnl
try:
    url = 'https://varantradarpro.pythonanywhere.com/api/simulation/daily_pnl'
    with opener.open(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=15) as resp:
        data = json.loads(resp.read().decode())
        print("Simulation daily_pnl:", data.get("status"), "Total trades:", data.get("summary", {}).get("total_trades"))
except Exception as e:
    print("daily_pnl error:", e)
