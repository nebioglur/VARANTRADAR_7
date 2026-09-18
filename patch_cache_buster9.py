# -*- coding: utf-8 -*-
with open('ui/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('style.css?v=8', 'style.css?v=9')
with open('ui/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
