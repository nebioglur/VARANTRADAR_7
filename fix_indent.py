with open('services/simulation_engine.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if "def __init__(self, daily_budget=100000.0, max_positions=999, owner=None):" in l:
        lines[i] = "    def __init__(self, daily_budget=100000.0, max_positions=999, owner=None):\n"
        lines[i+1] = "        self.daily_budget = daily_budget\n"
        lines[i+2] = "        self.max_positions = 999  # KULLANICI ISTEGI: Simulasyonda islem sayisi SINIRSIZ\n"
        lines[i+3] = "        self.owner = owner or \"local:nebioglur\"\n"
        break

with open('services/simulation_engine.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("Fixed indentation!")
