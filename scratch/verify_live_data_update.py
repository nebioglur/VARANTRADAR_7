import requests, time

time.sleep(3)
s = requests.Session()
s.headers.update({'User-Agent': 'Mozilla/5.0'})
s.post('https://varantradarpro.pythonanywhere.com/login', json={'username': 'nebioglur', 'password': '123'}, timeout=15)

# 1. Cache Status
r_cs = s.get('https://varantradarpro.pythonanywhere.com/api/cache_status', timeout=15)
print('PA Cache Status:', r_cs.json())

# 2. Dashboard Init
r_dash = s.get('https://varantradarpro.pythonanywhere.com/api/dashboard_init', timeout=15)
d_json = r_dash.json()
dash = d_json.get('dashboard_data', {})
print('PA Cache Date:', dash.get('cache_date'), 'last_updated:', d_json.get('last_updated'))
stats = dash.get('all_symbols_stats', {})
print('PA Symbols count:', len(stats))
for sym in ['BASGZ.IS', 'AYCES.IS', 'MEKAG.IS', 'LYDYE.IS']:
    if sym in stats:
        st = stats[sym]
        p = st.get('Price')
        c = st.get('Change_Pct')
        v = st.get('Vol_Multiplier')
        mv = st.get('Money_Volume')
        print(f'  {sym:10}: Price={p} Chg={c}% VolMult={v}x MoneyVol={mv}')

# 3. Tavan Adaylari & Opportunities 1h
print('PA Tavan adaylari count:', len(dash.get('tavan_adaylari', [])))
for t in dash.get('tavan_adaylari', [])[:3]:
    sym = t.get('Symbol') or t.get('symbol')
    price = t.get('Price') or t.get('price')
    print('  Tavan:', sym, price)

print('PA Opportunities 1h count:', len(dash.get('opportunities_1h', [])))
for o in dash.get('opportunities_1h', [])[:3]:
    sym = o.get('Symbol') or o.get('symbol')
    price = o.get('Price') or o.get('price')
    print('  Opp1h:', sym, price)

# 4. Dip Breakout
r_dip = s.get('https://varantradarpro.pythonanywhere.com/api/dip_breakout', timeout=15)
dip = r_dip.json()
print('PA Dip Breakout status:', dip.get('status'), 'rows:', len(dip.get('rows', [])))
if dip.get('rows'):
    for r in dip['rows'][:3]:
        print('  Dip row:', r.get('symbol'), r.get('category'), r.get('price'))
