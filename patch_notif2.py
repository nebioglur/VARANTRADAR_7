# -*- coding: utf-8 -*-
with open('services/notification_manager.py', 'r', encoding='utf-8') as f:
    text = f.read()

import re
text = text.replace('DAÐ KEKLÝÐÝ ', 'VIP ')

pattern = r'(phase = extra\.get\("Phase_Badge", "TAVAN RADARI"\))'
replacement = r'\1\n        if phase and "Erken" in phase:\n            return True\n'
text = re.sub(pattern, replacement, text)

with open('services/notification_manager.py', 'w', encoding='utf-8') as f:
    f.write(text)
print("NOTIF PATCH 2 OK")
