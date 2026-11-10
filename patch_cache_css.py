import re

with open('ui/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

# increment the version number in style.css?v=...
text = re.sub(r'style\.css\?v=[0-9a-zA-Z_]+', 'style.css?v=20260921_v2', text)
text = re.sub(r'app\.css\?v=[0-9a-zA-Z_]+', 'app.css?v=20260921_v2', text)

with open('ui/index.html', 'w', encoding='utf-8') as f:
    f.write(text)

print('Patched index.html cache busters')
