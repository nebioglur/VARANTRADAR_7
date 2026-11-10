import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('ui/app.js', 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

print("--- ui/app.js lines 3105-3140 ---")
for i in range(3104, min(3140, len(lines))):
    print(f"{i+1}: {lines[i]}", end='')
