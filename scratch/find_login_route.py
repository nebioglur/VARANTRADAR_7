with open('server.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if '@app.route(\'/login\'' in l or '@app.route("/login"' in l:
        print(f"Line {i}: {l}")
        for j in range(i, min(i+40, len(lines))):
            print(lines[j], end='')
