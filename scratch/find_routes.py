with open('server.py', 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if '@app.route(' in line:
        route_info = "".join(lines[i:i+5]).strip()
        if any(r in line for r in ['/', '/login', '/home', '<path']):
            print(f"Line {i+1}: {route_info}\n")
