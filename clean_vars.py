# -*- coding: utf-8 -*-
with open("ui/app.js", "r", encoding="utf-8") as f:
    code = f.read()

start_idx = code.find("function renderSuper12Table()")
ret_start = code.find("return '<tr>' +", start_idx)

# Remove the unused variable assignments right before return
chunk = code[start_idx:ret_start]
chunk_clean = chunk.replace("let prevClose = s.close || (s.price / (1 + (s.change / 100)));\n", "")
chunk_clean = chunk_clean.replace("let intraSign = s.intra_change > 0 ? '+' : '';\n", "")
chunk_clean = chunk_clean.replace("let intraColor = s.intra_change > 0 ? 'var(--accent-green)' : (s.intra_change < 0 ? 'var(--accent-red)' : 'var(--text-muted)');\n", "")

code = code[:start_idx] + chunk_clean + code[ret_start:]

with open("ui/app.js", "w", encoding="utf-8") as f:
    f.write(code)
print("Cleaned up unused variables.")
