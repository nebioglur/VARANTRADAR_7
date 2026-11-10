with open('services/telegram_bot.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for j in range(1048, 1095):
    print(lines[j], end='')
