with open('server.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i in range(670, 715):
    l = lines[i].encode('ascii', errors='replace').decode('ascii')
    print(f'{i+1}: {l.strip()[:100]}')
