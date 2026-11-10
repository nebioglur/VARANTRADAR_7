import urllib.request, json, http.cookiejar

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

login_data = json.dumps({'username': 'nebioglur', 'password': '123'}).encode('utf-8')
opener.open(urllib.request.Request('https://varantradarpro.pythonanywhere.com/login', data=login_data, headers={'Content-Type': 'application/json'}))

with opener.open(urllib.request.Request('https://varantradarpro.pythonanywhere.com/api/simulation/daily_pnl'), timeout=20) as resp:
    data = json.loads(resp.read().decode())
    print('Trades count:', len(data.get('trades', [])))
    for t in data.get('trades', []):
        sym = t.get('symbol')
        ent_p = t.get('entry_price')
        ex_p = t.get('exit_price')
        ent = f"{t.get('entry_time')} ({ent_p:.2f})" if ent_p else '-'
        ex = f"{t.get('exit_time')} ({ex_p:.2f})" if ex_p else '-'
        pnl = t.get('pnl_val', 0.0)
        reason = str(t.get('exit_reason', '')).encode('ascii', 'ignore').decode('ascii')
        print(f"{sym} | In: {ent} | Out: {ex} | PnL: {pnl:.2f} | Reason: {reason}")
