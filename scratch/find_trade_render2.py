with open('ui/app.js', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i in range(4647, 4750):
    l = lines[i].encode('ascii', errors='replace').decode('ascii')
    print(f'{i+1}: {l.strip()[:100]}')
