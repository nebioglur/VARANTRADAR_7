import re

with open('server.py', 'r', encoding='utf-8') as f:
    text = f.read()

# Add import if not present
if 'from zoneinfo import ZoneInfo' not in text:
    text = text.replace('from datetime import datetime, timedelta', 'from datetime import datetime, timedelta\nfrom zoneinfo import ZoneInfo')

# 1. bist_market_status
text = re.sub(r'now = now or datetime\.now\(\)', 'now = now or datetime.now(ZoneInfo(\"Europe/Istanbul\"))', text)

# 2. _collector_loop
text = re.sub(r'now = _dt\.now\(\)', 'now = _dt.now(ZoneInfo(\"Europe/Istanbul\"))', text)

# 3. _sim_loop (in background scanner)
text = re.sub(r'now = datetime\.now\(\)', 'now = datetime.now(ZoneInfo(\"Europe/Istanbul\"))', text)

with open('server.py', 'w', encoding='utf-8') as f:
    f.write(text)

print('Patched server.py')
