import urllib.request, http.cookiejar, json

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

login_data = json.dumps({'username': 'nebioglur', 'password': '123'}).encode('utf-8')
req = urllib.request.Request('https://varantradarpro.pythonanywhere.com/login', data=login_data, headers={'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'})
opener.open(req, timeout=15)

with opener.open(urllib.request.Request('https://varantradarpro.pythonanywhere.com/api/simulation/daily_pnl', headers={'User-Agent': 'Mozilla/5.0'}), timeout=15) as resp:
    data = json.loads(resp.read().decode())
    print('Daily PnL status:', data.get('status'))
    print('Current Balance:', data.get('current_balance'))
    print('Net PnL:', data.get('net_pnl'))
    perf = data.get('performance', {})
    print('Total Trades:', perf.get('total_trades'))
    print('Win Rate:', perf.get('win_rate'))
    eq = data.get('equity_curve', [])
    print('Equity curve days:', len(eq))
    if eq:
        print('Recent equity point:', eq[-1])
