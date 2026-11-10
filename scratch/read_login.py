import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('ui/login.html', 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

for i, l in enumerate(lines[350:]):
    print(f"{351+i}: {l}", end='')
