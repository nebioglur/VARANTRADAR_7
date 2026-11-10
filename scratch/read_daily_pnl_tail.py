with open('server.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()
for j in range(3110, min(3160, len(lines))):
    print(lines[j], end='')
