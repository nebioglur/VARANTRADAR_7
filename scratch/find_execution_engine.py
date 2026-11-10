with open('server.py', 'r', encoding='utf-8') as f:
    text = f.read()

import re
matches = re.findall(r'(\w+)\.evaluate\(', text)
print("Evaluate calls:", matches)
for m in re.finditer(r'evaluate\(', text):
    start = max(0, m.start() - 100)
    end = min(len(text), m.end() + 200)
    print("---")
    print(text[start:end])
