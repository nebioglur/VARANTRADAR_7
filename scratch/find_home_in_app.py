import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('ui/app.js', 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if any(k in l for k in ['home-wrapper', 'home-kpi', 'home-top-picks', 'fetchHome', 'home-committee', 'home-advice', 'tb-all-stocks-home']):
        print(f"Line {i+1}: {l.strip()[:100]}")
