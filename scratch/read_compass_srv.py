with open('server.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if 'def api_telegram_send_morning_compass' in l:
        print(f"Line {i}: {l.strip()}")
        for j in range(i, min(i+15, len(lines))):
            print(lines[j], end='')
        break
