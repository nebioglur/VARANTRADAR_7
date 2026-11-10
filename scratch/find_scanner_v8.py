with open('scanner/universal_scanner.py', 'r', encoding='utf-8') as f:
    text = f.read()

import re
for m in re.finditer(r'v8_', text):
    start = max(0, m.start() - 50)
    end = min(len(text), m.end() + 150)
    print("---")
    print(text[start:end])
