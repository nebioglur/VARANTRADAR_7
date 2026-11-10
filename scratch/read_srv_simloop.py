with open('server.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()[775:816]

for i, l in enumerate(lines):
    print(f'{i+776}: {l.strip()[:100]}')
