with open('services/market_data.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()[155:200]

for i, l in enumerate(lines):
    l_safe = l.encode('ascii', errors='replace').decode('ascii')
    print(f'{i+156}: {l_safe.strip()[:100]}')
