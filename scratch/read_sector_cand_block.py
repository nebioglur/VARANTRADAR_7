with open('services/simulation_engine.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()[540:635]

for i, l in enumerate(lines):
    l_safe = l.encode('ascii', errors='replace').decode('ascii')
    print(f'{i+541}: {l_safe.strip()[:100]}')
