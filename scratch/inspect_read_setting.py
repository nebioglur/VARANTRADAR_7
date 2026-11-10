with open('services/telegram_bot.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if 'def _read_persistent_setting' in l:
        print(f"--- Line {i}: {l.strip()} ---")
        for j in range(i, min(i+25, len(lines))):
            print(lines[j], end='')
