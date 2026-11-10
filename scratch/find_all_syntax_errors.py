import sys
import re
sys.stdout.reconfigure(encoding='utf-8')

with open('ui/app.js', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

# Look for patterns like }"> or }'> or similar stray closures
matches = re.finditer(r'\}\s*[\"\']>|[\"\']>\s*\}', text)
for m in matches:
    start = max(0, m.start() - 40)
    end = min(len(text), m.end() + 40)
    print("Match around:", repr(text[start:end]))
