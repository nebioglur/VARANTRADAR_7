# -*- coding: utf-8 -*-
with open('ui/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('app.js?v=20260913_v2', 'app.js?v=20260913_v3')
with open('ui/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
