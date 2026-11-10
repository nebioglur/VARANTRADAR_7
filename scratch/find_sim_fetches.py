with open('ui/app.js', 'r', encoding='utf-8') as f:
    text = f.read()

import re
matches = re.findall(r'fetch\([\'\"][^\'\"]*[\'\"]\)', text)
sim_fetches = [m for m in set(matches) if 'trade' in m.lower() or 'sim' in m.lower() or 'pnl' in m.lower()]
for m in sorted(sim_fetches):
    print(m)
