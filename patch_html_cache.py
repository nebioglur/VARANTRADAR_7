# -*- coding: utf-8 -*-
with open('ui/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

import re
old_script = r'<script src="app.js\?v=[^"]+"></script>'
new_script = r'<script src="app.js?v=20260912_v3"></script>'
content = re.sub(old_script, new_script, content)

with open('ui/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("CACHE_BUST_HTML_YAZILDI")
