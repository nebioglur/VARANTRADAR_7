with open('services/telegram_bot.py', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

import re
matches = re.findall(r'def\s+(\w+)\s*\(', text)
print("Functions in services/telegram_bot.py:")
for m in matches:
    print(" ", m)

print("\n--- First 60 lines of services/telegram_bot.py ---")
for l in text.splitlines()[:60]:
    print(l)
