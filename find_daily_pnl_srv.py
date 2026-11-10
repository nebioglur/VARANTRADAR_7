with open('server.py', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find('def api_simulation_daily_pnl')
print('Found api_simulation_daily_pnl at:', idx)
print(text[idx:idx+1500])
