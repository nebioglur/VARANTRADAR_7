import os

found = []
for root, dirs, files in os.walk('.'):
    for f in files:
        if f.endswith(('.py', '.sh', '.bat', '.json', '.env', '.txt')) and not root.startswith('./.git') and not 'scratch' in root:
            p = os.path.join(root, f)
            try:
                with open(p, 'r', encoding='utf-8') as fp:
                    c = fp.read()
                    if 'proxy.server' in c or '3128' in c:
                        found.append(p)
            except:
                pass
print("Found in:", found)
