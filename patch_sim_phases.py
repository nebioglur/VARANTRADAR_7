# -*- coding: utf-8 -*-
with open('services/simulation_engine.py', 'r', encoding='utf-8') as f:
    text = f.read()

import re
pattern = r'phase in \[[^\]]+\]:'
replacement = r'phase in ["Erken Kopuþ (Phase 1)", "Ývmelenme (Phase 2)", "Kilitleme Baskýsý (Phase 3)"]:'

text = re.sub(pattern, replacement, text)

with open('services/simulation_engine.py', 'w', encoding='utf-8') as f:
    f.write(text)
print("PHASES PATCH OK")
