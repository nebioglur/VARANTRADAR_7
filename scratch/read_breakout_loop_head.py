with open('server.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for j in range(4170, 4215):
    print(f"{j+1}: {lines[j]}", end='')
