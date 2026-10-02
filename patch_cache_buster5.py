# -*- coding: utf-8 -*-
with open('ui/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('app.js?v=20260913_v5', 'app.js?v=20260913_v6')
content = content.replace('app.js?v=20260913_v4', 'app.js?v=20260913_v6')
content = content.replace('app.js?v=20260913_v3', 'app.js?v=20260913_v6')
with open('ui/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
