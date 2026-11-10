with open('ui/login.html', 'r', encoding='utf-8') as f:
    text = f.read()

import re
matches = [m.start() for m in re.finditer(r'apk', text, re.I)]
for idx in matches:
    print(text[max(0, idx-100):min(len(text), idx+150)])
    print('-'*50)
