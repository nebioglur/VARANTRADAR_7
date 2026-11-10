with open('services/market_data.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()[80:115]

for i, l in enumerate(lines):
    l_safe = l.encode('ascii', errors='replace').decode('ascii')
    print(f'{i+81}: {l_safe.strip()[:100]}')
