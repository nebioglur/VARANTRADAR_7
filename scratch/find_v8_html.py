with open('ui/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

import re
matches = [m.start() for m in re.finditer(r'refreshV8Data', text)]
print("refreshV8Data in index.html matches:", len(matches))
for idx in matches:
    print(text[idx-50:idx+300])
    print('='*50)
