with open('ui/app.js', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i in range(4605, 4710):
    print(f'{i+1}: {lines[i].strip()[:100]}')
