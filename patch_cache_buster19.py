# -*- coding: utf-8 -*-
with open('ui/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('app.js?v=20260913_v18', 'app.js?v=20260913_v19')
with open('ui/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
