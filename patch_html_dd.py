# -*- coding: utf-8 -*-
import re

with open('ui/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Tum Hisseler thead guncellemesi (Sortable headers in tb-all-stocks-home)
text = re.sub(r'(<th.*?onclick="sortAllStocks\([^)]*\'rel_vol\'\).*?</th>)', r'\1\n                                      <th>D/D (Saat-Gun)</th>', text)

# 2. Super12 thead guncellemesi (Static headers)
text = re.sub(r'(<th>Hacim Gucu %</th>)', r'\1\n                        <th>D/D (Saat-Gun)</th>', text)

with open('ui/index.html', 'w', encoding='utf-8') as f:
    f.write(text)

print("INDEX HTML S/R HEADER PATCH OK")
