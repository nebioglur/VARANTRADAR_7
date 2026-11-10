with open('services/simulation_engine.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()[470:485]

for i, l in enumerate(lines):
    print(repr(l))
