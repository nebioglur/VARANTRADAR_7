import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('pro8_app.js', 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

for i, l in enumerate(lines[:80]):
    if 'vrAuthorizedFetch' in l or 'vrReportError' in l:
        print(f"{i+1}: {l}", end='')
