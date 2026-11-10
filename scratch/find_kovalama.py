import os, glob

for root, dirs, files in os.walk('.'):
    if '.git' in root or '__pycache__' in root or 'node_modules' in root:
        continue
    for f in files:
        if f.endswith('.py'):
            p = os.path.join(root, f)
            try:
                with open(p, 'r', encoding='utf-8', errors='ignore') as fl:
                    cnt = fl.read()
                    if 'kovalama' in cnt:
                        print(f"Found in {p}")
            except Exception as e:
                pass
