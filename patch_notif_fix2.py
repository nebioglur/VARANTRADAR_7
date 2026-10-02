# -*- coding: utf-8 -*-
with open('services/notification_manager.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace(r'\nclass NotificationManager:', '\nclass NotificationManager:')

with open('services/notification_manager.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("PATCH_NOTIF_FIX_OK")
