import re

with open('ui/index.html', 'r', encoding='utf-8', errors='ignore') as f:
    html = f.read()

matches = re.findall(r'id=["\']([^"\']*home[^"\']*)["\']', html, re.I)
print('IDs with home in index.html:', matches)

sections = re.findall(r'<section[^>]*id=["\']([^"\']+)["\']', html)
print('All section IDs:', sections)

divs = re.findall(r'<div[^>]*id=["\']([^"\']+)["\']', html)
print('Div IDs count:', len(divs))
for d in divs:
    if 'home' in d.lower() or 'tab' in d.lower() or 'view' in d.lower():
        print('  matching div id:', d)
