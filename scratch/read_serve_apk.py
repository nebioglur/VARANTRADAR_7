with open('server.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if 'def serve_apk' in l:
        print(f"Line {i}: {l.strip()}")
        for j in range(max(0, i-3), min(i+15, len(lines))):
            print(lines[j], end='')
        break
