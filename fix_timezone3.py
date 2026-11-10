import re

with open('server.py', 'r', encoding='utf-8') as f:
    text = f.read()

# 1. get_next_run_seconds
text = text.replace('now = datetime.datetime.now()', 'from zoneinfo import ZoneInfo\n            now = datetime.datetime.now(ZoneInfo(\"Europe/Istanbul\"))')

# 2. fakeout zone
text = text.replace('now_time = datetime.datetime.now().time()', 'from zoneinfo import ZoneInfo\n        now_time = datetime.datetime.now(ZoneInfo(\"Europe/Istanbul\")).time()')

with open('server.py', 'w', encoding='utf-8') as f:
    f.write(text)

print('Patched server.py datetime.datetime.now()')
