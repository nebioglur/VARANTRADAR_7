with open('server.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()[695:716]

for i, l in enumerate(lines):
    print(f'{i+696}: {l.strip()[:100]}')
