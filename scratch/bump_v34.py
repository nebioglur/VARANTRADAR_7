with open('ui/index.html', 'r', encoding='utf-8') as f:
    h = f.read()

h = h.replace('style.css?v=20261106_v31', 'style.css?v=20261106_v34')
h = h.replace('app.js?v=20261106_v33', 'app.js?v=20261106_v34')
h = h.replace('/sw.js?v=20261106_v33', '/sw.js?v=20261106_v34')

with open('ui/index.html', 'w', encoding='utf-8') as f:
    f.write(h)

with open('ui/sw.js', 'r', encoding='utf-8') as f:
    s = f.read()

import re
s = re.sub(r'varantradar-v\d+', 'varantradar-v34', s)
s = re.sub(r'CACHE_NAME = [\'\"].*?[\'\"]', "CACHE_NAME = 'varantradar-v34'", s)

with open('ui/sw.js', 'w', encoding='utf-8') as f:
    f.write(s)

print("Bumped to v34 in index.html and sw.js")
