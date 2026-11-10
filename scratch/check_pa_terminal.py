import urllib.request, http.cookiejar, json

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

login_data = json.dumps({'username': 'nebioglur', 'password': '123'}).encode('utf-8')
req = urllib.request.Request('https://varantradarpro.pythonanywhere.com/login', data=login_data, headers={'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'})
opener.open(req, timeout=15)

with opener.open(urllib.request.Request('https://varantradarpro.pythonanywhere.com/api/simulation/terminal', headers={'User-Agent': 'Mozilla/5.0'}), timeout=15) as resp:
    data = json.loads(resp.read().decode())
    print('Terminal status:', data.get('status'))
    term = data.get('terminal', {})
    print('Terminal keys:', list(term.keys()))
    pos = term.get('open_positions', [])
    print('Open positions count:', len(pos))
    closed = term.get('closed_trades', [])
    print('Closed trades count:', len(closed))
    if closed:
        print('Sample closed trade:', closed[0])
