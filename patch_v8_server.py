# -*- coding: utf-8 -*-
with open('server.py', 'r', encoding='utf-8') as f:
    content = f.read()

import re
old_bo = r'(bo\["price"\] = data\.get\("Daily_Close", 0\.0\))'
new_bo = r'bo["symbol"] = sym\n            \1'
content = re.sub(old_bo, new_bo, content)

old_disc = r'(disc\["price"\] = data\.get\("Daily_Close", 0\.0\))'
new_disc = r'disc["symbol"] = sym\n            \1'
content = re.sub(old_disc, new_disc, content)

with open('server.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("V8_API_DUZELTILDI")
