with open('ui/app.js', 'r', encoding='utf-8', errors='ignore') as f:
    app_js = f.read()

import re
print("Occurrences of 'home' in app.js:")
for m in re.finditer(r'([^\n]*home[^\n]*)', app_js, re.I):
    print("  ", m.group(1)[:120])
