with open('services/telegram_bot.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for j in range(840, min(900, len(lines))):
    print(lines[j], end='')
