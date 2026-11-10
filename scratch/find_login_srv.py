with open('server.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if '/login' in l and '@app.route' in l:
        for j in range(i, min(len(lines), i+25)):
            print(f'{j+1}: {lines[j].strip()[:90]}')
        break
