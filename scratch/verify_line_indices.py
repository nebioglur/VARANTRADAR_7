with open('services/simulation_engine.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if "valid_signals = []" in l:
        start_eval = i
    if "if not selected:" in l and i > 500:
        end_eval = i + 2
    if "to_remove = []" in l and i > 700:
        start_buy = i
    if "for s in to_remove:" in l and i > 700:
        end_buy = i + 4

print("start_eval:", start_eval+1, repr(lines[start_eval]))
print("end_eval:", end_eval+1, repr(lines[end_eval]))
print("start_buy:", start_buy+1, repr(lines[start_buy]))
print("end_buy:", end_buy+1, repr(lines[end_buy]))
