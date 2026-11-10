with open('services/simulation_engine.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if 'final_stop' in l or 'strat_title' in l:
        print(f'{i+1}: {l.strip()[:100]}')
