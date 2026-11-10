# -*- coding: utf-8 -*-
with open("ui/app.js", "r", encoding="utf-8") as f:
    code = f.read()

bad1 = "if (countTotal) countTotal.textContent = data.length;"
good1 = "if (countTotal) countTotal.textContent = (window.globalDashboardData && window.globalDashboardData.all_symbols_stats) ? Object.keys(window.globalDashboardData.all_symbols_stats).length : data.length;"

bad2 = "Sistem ${data.length} hisseyi"
good2 = "Sistem ${(window.globalDashboardData && window.globalDashboardData.all_symbols_stats) ? Object.keys(window.globalDashboardData.all_symbols_stats).length : 550} hisseyi"

code = code.replace(bad1, good1)
code = code.replace(bad2, good2)

with open("ui/app.js", "w", encoding="utf-8") as f:
    f.write(code)
print("Fixed V8 total scanned counts!")
