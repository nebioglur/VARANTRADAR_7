with open('server.py', 'r', encoding='utf-8') as f:
    text = f.read()

import re
matches = [m.start() for m in re.finditer(r'Android Uygulamas', text)]
for idx in matches:
    print(text[idx-100:idx+200])
