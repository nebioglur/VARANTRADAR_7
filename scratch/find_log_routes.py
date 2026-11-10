with open('server.py', 'r', encoding='utf-8') as f:
    text = f.read()

import re
routes = [r for r in re.findall(r'@app\.route\([\'"]([^\'"]+)[\'"]', text) if 'log' in r]
print('Log routes:', routes)
