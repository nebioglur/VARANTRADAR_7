
import re
with open('ui/index.html', encoding='utf-8') as f:
    html = f.read()
new_html = re.sub(r'app.js\?v=20260819_v21', 'app.js?v=20260820_v22', html)
with open('ui/index.html', 'w', encoding='utf-8') as f:
    f.write(new_html)

