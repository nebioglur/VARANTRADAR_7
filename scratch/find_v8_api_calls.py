with open('ui/app.js', 'r', encoding='utf-8') as f:
    text = f.read()

import re
matches = re.findall(r'(/api/v8/[^\s\'"`\)\?]+)', text)
print("Unique V8 API calls in ui/app.js:")
for m in sorted(set(matches)):
    print(" ", m)
