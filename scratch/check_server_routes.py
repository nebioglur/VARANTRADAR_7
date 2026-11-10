with open('server.py', 'r', encoding='utf-8', errors='ignore') as f:
    server_py = f.read()

import re
matches = re.findall(r'@app\.route\([^\)]+\)\s+def \w+\([^\)]*\):[^:]+?(?=@app|\Z)', server_py, re.DOTALL)
for m in matches:
    if '/' in m and ('index' in m or 'home' in m or 'login' in m or 'route(\'/\'' in m):
        print(m[:300])
        print("="*40)
