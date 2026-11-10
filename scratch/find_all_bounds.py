with open('services/simulation_engine.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for idx, l in enumerate(lines):
    if "valid_signals = []" in l:
        print(f"valid_signals = [] at line {idx+1}")
    if "valid_signals.sort" in l:
        print(f"valid_signals.sort at line {idx+1}")
    if "selected = valid_signals[:effective_max_positions]" in l:
        print(f"selected = valid_signals[:effective_max_positions] at line {idx+1}")
    if "for current_time in sorted_times:" in l:
        print(f"for current_time in sorted_times: at line {idx+1}")
    if "to_remove = []" in l and idx > 800:
        print(f"to_remove = [] at line {idx+1}")
    if "for s in to_remove:" in l and idx > 800:
        print(f"for s in to_remove: at line {idx+1}")
    if "close_open_now" in l:
        print(f"close_open_now at line {idx+1}")
