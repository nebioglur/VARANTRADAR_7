with open('services/simulation_engine.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i in range(895, 940):
    l = lines[i].encode('ascii', errors='replace').decode('ascii')
    print(f'{i+1}: {l.strip()[:100]}')
