# -*- coding: utf-8 -*-
with open("server.py", "r", encoding="utf-8") as f:
    text = f.read()

import re
text = re.sub(r'if score >= 80 and "YATAY" not in phase.*?:', 'if score >= 80 and "NEGAT" not in phase and "UZAK DUR" not in phase:', text)

with open("server.py", "w", encoding="utf-8") as f:
    f.write(text)

print("LIVE PATCH DONE")
