with open('services/simulation_engine.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

print(f"Total lines in simulation_engine.py: {len(lines)}")
for i, l in enumerate(lines):
    if any(k in l for k in ['def run_simulation', 'def execute_simulation', 'boga', 'offensive', 'bull']):
        print(f"Line {i}: {l.strip()}")
