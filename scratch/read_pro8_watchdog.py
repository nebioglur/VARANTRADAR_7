import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('pro8_app.js', 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

print("--- pro8_app.js lines 90-130 ---")
for i in range(89, min(130, len(lines))):
    print(f"{i+1}: {lines[i]}", end='')
