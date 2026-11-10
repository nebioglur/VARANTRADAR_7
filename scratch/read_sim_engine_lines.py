with open('services/simulation_engine.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for j in range(310, 360):
    print(lines[j], end='')
