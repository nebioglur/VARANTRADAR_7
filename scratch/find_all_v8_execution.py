import os

for root, dirs, files in os.walk('.'):
    if any(k in root for k in ['.git', '.cache', 'scratch']): continue
    for f in files:
        if f.endswith('.py'):
            p = os.path.join(root, f)
            try:
                with open(p, 'r', encoding='utf-8') as fp:
                    c = fp.read()
                    if 'v8_execution' in c:
                        print(f"Found v8_execution in: {p}")
            except:
                pass
