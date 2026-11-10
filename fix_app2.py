# -*- coding: utf-8 -*-
with open("ui/app.js", "r", encoding="utf-8") as f:
    code = f.read()

idx = code.find("let intraColor = s.intra_change > 0 ? 'var(--accent-green)' : (s.intra_change < 0 ? 'var(--accent-red)' : 'var(--text-muted)');")
if idx == -1:
    print("Could not find anchor string!")
else:
    # get 500 chars around idx
    print(code[idx-50:idx+800])
