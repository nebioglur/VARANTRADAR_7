# -*- coding: utf-8 -*-
with open('server.py', 'r', encoding='utf-8') as f:
    content = f.read()

import re
content = re.sub(r"if request\.path in allowed: return", "if request.path in allowed or request.path.startswith('/api/dashboard_init'): return", content)

with open('server.py', 'w', encoding='utf-8') as f:
    f.write(content)
