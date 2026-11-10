import re

with open('ui/index.html', 'r', encoding='utf-8') as f:
    text = f.read()
matches = re.findall(r'href=[\'"][^\'"]*apk[^\'"]*[\'"]', text, re.I)
print('index.html apk matches:', matches)

with open('ui/app.js', 'r', encoding='utf-8') as f:
    text2 = f.read()
matches2 = re.findall(r'[\'"][^\'"]*apk[^\'"]*[\'"]', text2, re.I)
print('app.js apk matches:', matches2[:10])
