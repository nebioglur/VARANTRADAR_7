with open('server.py', 'r', encoding='utf-8') as f:
    text = f.read()

import re
matches = [m.start() for m in re.finditer(r'TAVAN RİSKİ', text)]
print("TAVAN RISKI matches in server.py:", len(matches))
for m in matches:
    print(text[m-200:m+400])
    print("="*50)
