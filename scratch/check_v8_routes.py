with open('server.py', 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if '@app.route(\'/api/v8/' in l:
        print(f"L{i+1}: {l.strip()}")
        for j in range(i, min(len(lines), i+20)):
            if 'return' in lines[j] or 'except' in lines[j]:
                print(f"   {j+1}: {lines[j].strip()}")
