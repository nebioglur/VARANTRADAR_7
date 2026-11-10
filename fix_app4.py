# -*- coding: utf-8 -*-
with open("ui/app.js", "r", encoding="utf-8") as f:
    code = f.read()

idx = code.find("let intraColor = s.intra_change > 0")
print(code[idx-500:idx+500])
