with open('server.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()[703:714]

for i, l in enumerate(lines):
    print(repr(l))
