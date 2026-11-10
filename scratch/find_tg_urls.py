with open('services/telegram_bot.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if 'api.telegram.org' in l:
        print(f"Line {i}: {l.strip()}")
