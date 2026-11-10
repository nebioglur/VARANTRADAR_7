with open('ui/app.js', 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if 'fetchSimulationData' in l or 'runVarantSimulation' in l or 'api/simulation' in l:
        print(f"L{i+1}: {l.strip()[:100]}")
