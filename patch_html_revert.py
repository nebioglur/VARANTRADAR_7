# -*- coding: utf-8 -*-
import re

with open('ui/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

# Remove the D/D headers
text = re.sub(r'\s*<th>D/D \(Saat-Gun\)</th>', '', text)

with open('ui/index.html', 'w', encoding='utf-8') as f:
    f.write(text)

print("HTML REVERT OK")
