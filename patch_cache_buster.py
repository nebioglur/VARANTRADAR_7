# -*- coding: utf-8 -*-
with open('ui/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# JS Cache Buster guncelle
content = content.replace('app.js?v=20260912_v3', 'app.js?v=20260913_v1')
content = content.replace('app-auth.js?v=20260912_v4', 'app-auth.js?v=20260913_v1')
content = content.replace('app.css?v=20260902', 'app.css?v=20260913_v1')

with open('ui/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("CACHE_BUSTER_UPDATED")
