# -*- coding: utf-8 -*-
with open("ui/app.js", "r", encoding="utf-8") as f:
    code = f.read()

bad1 = "if (countTotal) countTotal.textContent = (window.globalDashboardData && window.globalDashboardData.all_symbols_stats) ? Object.keys(window.globalDashboardData.all_symbols_stats).length : data.length;"
good1 = "if (countTotal) countTotal.textContent = (typeof globalDashboardData !== 'undefined' && globalDashboardData.all_symbols_stats) ? Object.keys(globalDashboardData.all_symbols_stats).length : 550;"

bad2 = "Sistem ${(window.globalDashboardData && window.globalDashboardData.all_symbols_stats) ? Object.keys(window.globalDashboardData.all_symbols_stats).length : 550} hisseyi taryor."
# Due to encoding on PowerShell in previous edit, the char was corrupted to 'taryor.'
# We should use regex to replace it properly.
import re
code = code.replace(bad1, good1)

pattern = r"Sistem \$\{\(window\.globalDashboardData && window\.globalDashboardData\.all_symbols_stats\) \? Object\.keys\(window\.globalDashboardData\.all_symbols_stats\)\.length : 550\} hisseyi tar[^\s]*"
replacement = r"Sistem ${(typeof globalDashboardData !== 'undefined' && globalDashboardData.all_symbols_stats) ? Object.keys(globalDashboardData.all_symbols_stats).length : 550} hisseyi tarıyor."
code = re.sub(pattern, replacement, code)

with open("ui/app.js", "w", encoding="utf-8") as f:
    f.write(code)
print("Fixed countTotal in UI.")
