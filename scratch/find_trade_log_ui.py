with open('ui/app.js', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if any(k in l.lower() for k in ['trade log', 'işlem geçmişi', 'daily_pnl', 'loadtrades', 'rendertrades', 'gettrades']):
        print(f'{i+1}: {l.strip()[:100]}')
