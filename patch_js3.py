# -*- coding: utf-8 -*-
with open('live_app.js', 'r', encoding='utf-8') as f:
    content = f.read()

import re
old_js = r"function renderAllDashboardTables\(\) {\s*const cats ="
new_js = r"function renderAllDashboardTables() {\n    renderAllStocksTable();\n    const cats ="

content = re.sub(old_js, new_js, content)

with open('live_app.js', 'w', encoding='utf-8') as f:
    f.write(content)
print("JS3_YAZILDI")
