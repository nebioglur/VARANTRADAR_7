# -*- coding: utf-8 -*-
with open('analysis/technical.py', 'r', encoding='utf-8') as f:
    text = f.read()

import re
# Insert the volume check right after vol_multiplier = ...
pattern = r'(vol_multiplier = round\(current_vol / avg_vol_20, 1\) if avg_vol_20 > 0 else 1\.0)'
replacement = r'\1\n            \n            if vol_multiplier < 1.5:\n                return None\n'

text = re.sub(pattern, replacement, text)

with open('analysis/technical.py', 'w', encoding='utf-8') as f:
    f.write(text)
print("TECH PATCH 2 OK")
