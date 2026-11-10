with open('ui/index.html', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

import re
matches = [m.start() for m in re.finditer(r'id=["\'][^"\']*v8[^"\']*["\']', text)]
for idx in matches:
    print(text[max(0, idx-20):min(len(text), idx+120)])
    print('---')
