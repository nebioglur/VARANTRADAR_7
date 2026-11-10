with open('services/market_data.py', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

import re
matches = re.findall(r'def\s+(\w+)\s*\(', text)
print("Functions in services/market_data.py:", matches)

lines = text.splitlines()
for i, l in enumerate(lines):
    if 'def record_signals' in l:
        print(f"L{i+1}:")
        for j in range(i, min(len(lines), i+30)):
            print(f"{j+1}: {lines[j]}")
        break
