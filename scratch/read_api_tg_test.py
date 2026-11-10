with open('server.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if 'def api_telegram_test' in l:
        print(f"Line {i}:")
        for j in range(i, min(i+25, len(lines))):
            print(lines[j], end='')
        break
