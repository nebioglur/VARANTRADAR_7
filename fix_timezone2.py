import re

with open('services/live_trade_monitor.py', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace('now = datetime.now()', 'from zoneinfo import ZoneInfo\n    now = datetime.now(ZoneInfo(\"Europe/Istanbul\"))')

with open('services/live_trade_monitor.py', 'w', encoding='utf-8') as f:
    f.write(text)

print('Patched services/live_trade_monitor.py')
