with open('services/simulation_engine.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()[225:285]

for i, l in enumerate(lines):
    l_safe = l.encode('ascii', errors='replace').decode('ascii')
    print(f'{i+226}: {l_safe.strip()[:100]}')
