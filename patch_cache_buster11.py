# -*- coding: utf-8 -*-
with open('ui/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('style.css?v=10', 'style.css?v=11')
with open('ui/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
