with open('services/simulation_engine.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i in range(498, 520):
    l = lines[i].encode('ascii', errors='replace').decode('ascii')
    print(f'{i+1}: {l.strip()[:100]}')

print("...")
for i in range(645, 665):
    l = lines[i].encode('ascii', errors='replace').decode('ascii')
    print(f'{i+1}: {l.strip()[:100]}')
