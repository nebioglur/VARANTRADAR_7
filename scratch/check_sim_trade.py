import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('services/telegram_bot.py', 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if 'def notify_sim_trade' in l:
        print(f"L{i+1}:")
        for j in range(i, min(len(lines), i+60)):
            print(f"{j+1}: {lines[j]}", end='')
        break
