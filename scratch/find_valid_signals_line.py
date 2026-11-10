with open('services/simulation_engine.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if 'valid_signals = []' in l:
        print(f"valid_signals = [] at line {i+1}")
        for j in range(i, min(len(lines), i+15)):
            print(repr(lines[j]))
        break
