with open('server.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i in range(2850, 2950):
    print(f'{i+1}: {lines[i].strip()[:100]}')
