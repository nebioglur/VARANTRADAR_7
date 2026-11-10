import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('pro8_app.js', 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

for i in range(34, 75):
    print(f"{i+1}: {lines[i]}", end='')
