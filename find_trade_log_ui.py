with open('ui/app.js', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find('İşlem Geçmişi (Trade Log)')
if idx == -1:
    idx = text.find('Trade Log')
print('Found Trade Log in ui/app.js at:', idx)
if idx != -1:
    print(text[max(0, idx-200):idx+800])

idx_api = text.find('/api/simulation/daily_pnl')
print('daily_pnl fetch at:', idx_api)
if idx_api != -1:
    print(text[max(0, idx_api-100):idx_api+600])
