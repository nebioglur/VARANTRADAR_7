import os

for root, dirs, files in os.walk('.'):
    if any(k in root for k in ['.git', '.cache', 'scratch']): continue
    for f in files:
        if f.endswith(('.js', '.html', '.py')):
            p = os.path.join(root, f)
            try:
                with open(p, 'r', encoding='utf-8') as fp:
                    c = fp.read()
                    if 'refreshV8Data' in c:
                        print(f"Found refreshV8Data in: {p}")
            except:
                pass
