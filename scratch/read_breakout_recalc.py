with open('server.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for j in range(4180, 4235):
    print(f"{j+1}: {lines[j]}", end='')
