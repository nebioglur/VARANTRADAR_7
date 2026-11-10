with open('services/simulation_engine.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if 'if score >= minimum_score' in l:
        print(f"found at {i+1}")
        for j in range(i, min(len(lines), i+85)):
            print(repr(lines[j]))
        break
