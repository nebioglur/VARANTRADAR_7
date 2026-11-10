with open('server.py', 'r', encoding='utf-8') as f:
    text = f.read()

import re
matches = [m.start() for m in re.finditer(r'v8_execution', text)]
print("v8_execution in server.py:", len(matches))
for m in matches:
    print("---")
    print(text[m-100:m+200])
