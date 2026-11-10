with open('ui/app.js', 'r', encoding='utf-8') as f:
    text = f.read()

import re
print("Matches in app.js:")
for m in re.finditer(r'(v8|breakout|discovery|regime|playbook)', text, re.I):
    start = max(0, m.start() - 30)
    end = min(len(text), m.end() + 50)
    print(" ", text[start:end].replace('\n', ' '))
    if m.start() > 50000: break
