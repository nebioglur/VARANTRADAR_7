with open('server.py', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find('def api_simulation_daily_pnl')
print(text[idx+3200:idx+4500])
