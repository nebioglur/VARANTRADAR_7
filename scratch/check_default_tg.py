with open('services/telegram_bot.py', 'r', encoding='utf-8') as f:
    text = f.read()

import re
for m in re.finditer(r'DEFAULT_(BOT_TOKEN|CHAT_ID)\s*=\s*[^\n]+', text):
    print(m.group(0))
