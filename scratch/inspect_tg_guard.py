with open('services/telegram_bot.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if 'is_authorized_telegram_sender' in l:
        print(f"--- Line {i}: {l.strip()} ---")
        for j in range(i, min(i+40, len(lines))):
            print(lines[j], end='')
