import sys
with open('ui/app.js', 'r', encoding='utf-8') as f:
    content = f.read()

import re
# We need to remove the frontend EMA 50/200 filter in renderAllDashboardTables
pattern = r'// EMA 50 & 200 filtresini her zaman uygula.*?if \(items\.length === 0\) \{\s*tbody\.innerHTML = [^}]+\}\s*continue;\s*\}'
content = re.sub(pattern, '', content, flags=re.DOTALL)

with open('ui/app.js', 'w', encoding='utf-8') as f:
    f.write(content)

with open('live_app.js', 'r', encoding='utf-8') as f:
    content2 = f.read()
content2 = re.sub(pattern, '', content2, flags=re.DOTALL)
with open('live_app.js', 'w', encoding='utf-8') as f:
    f.write(content2)
print('Removed EMA filter')
