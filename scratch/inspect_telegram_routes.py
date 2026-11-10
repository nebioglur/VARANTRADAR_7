with open('server.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if '/api/telegram/' in l and '@app.route' in l:
        print(f"--- Line {i}: {l.strip()} ---")
        for j in range(i, min(i+35, len(lines))):
            print(lines[j], end='')
