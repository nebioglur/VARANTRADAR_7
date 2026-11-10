with open('services/market_data.py', 'r', encoding='utf-8') as f:
    text = f.read()

import re
matches = [m.start() for m in re.finditer(r'proxy', text, re.I)]
print("Proxy in market_data count:", len(matches))
for idx in matches:
    print(text[max(0, idx-50):min(len(text), idx+100)])
