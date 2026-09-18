with open("services/simulation_engine.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if "if score >= minimum_score and phase in [" in line:
        line = '            if score >= minimum_score and any(p in phase for p in ["Phase 1", "Phase 2", "Phase 3"]):' + '\n'
    new_lines.append(line)

with open("services/simulation_engine.py", "w", encoding="utf-8") as f:
    f.writelines(new_lines)

print("PHASES PATCH 2 OK")
