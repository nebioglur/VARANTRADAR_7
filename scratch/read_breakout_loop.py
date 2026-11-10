with open('server.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for j in range(4210, 4265):
    print(f"{j+1}: {lines[j]}", end='')
