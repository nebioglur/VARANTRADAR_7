with open('server.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if 'def api_simulation_daily_pnl' in l:
        for j in range(i+170, min(i+215, len(lines))):
            print(lines[j], end='')
        break
