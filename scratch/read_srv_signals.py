with open('server.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()[670:720]

for i, l in enumerate(lines):
    l_safe = l.encode('ascii', errors='replace').decode('ascii')
    print(f'{i+671}: {l_safe.strip()[:100]}')
