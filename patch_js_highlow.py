# -*- coding: utf-8 -*-
import re

with open('ui/app.js', 'r', encoding='utf-8') as f:
    text = f.read()

# Replace all occurrences of price: price,\n              change: change,
text = re.sub(r'(price: price,\s*change: change,)', r'\1\n              high: data.High || price,\n              low: data.Low || price,', text)

with open('ui/app.js', 'w', encoding='utf-8') as f:
    f.write(text)

print("JS HIGHLOW PATCH OK")
