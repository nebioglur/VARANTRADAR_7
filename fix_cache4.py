import re

with open('ui/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

text = re.sub(r'style\.css\?v=[0-9a-zA-Z_]+', 'style.css?v=20260921_v4', text)

with open('ui/index.html', 'w', encoding='utf-8') as f:
    f.write(text)

print('Patched index.html cache busters to v4')
