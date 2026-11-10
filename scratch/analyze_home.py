import re
import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('pro8_app.js', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

lines = text.splitlines()

print("Searching for home references in pro8_app.js:")
for i, line in enumerate(lines):
    if 'home' in line.lower() and not line.strip().startswith('//'):
        print(f"L{i+1}: {line.strip()[:140]}")
