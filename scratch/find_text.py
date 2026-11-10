import os

for root, dirs, files in os.walk('.'):
    for f in files:
        if f.endswith(('.html', '.js', '.py', '.json')) and not root.startswith('./.git') and not root.startswith('./.cache') and not 'scratch' in root:
            p = os.path.join(root, f)
            try:
                with open(p, 'r', encoding='utf-8') as fp:
                    content = fp.read()
                    if 'Android Uygulamasını' in content:
                        print('Found in:', p)
            except:
                pass
