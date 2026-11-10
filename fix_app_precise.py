# -*- coding: utf-8 -*-
with open("ui/app.js", "r", encoding="utf-8") as f:
    code = f.read()

# Find the start of renderSuper12Table
start_idx = code.find("function renderSuper12Table()")
if start_idx == -1:
    print("Function not found!")
    exit(1)

# Find the return '<tr>' block inside renderSuper12Table
ret_start = code.find("return '<tr>' +", start_idx)
ret_end = code.find("</tr>';", ret_start) + len("</tr>';")

if ret_start == -1 or ret_end == -1:
    print("Return block not found!")
    exit(1)

old_block = code[ret_start:ret_end]
print("Found old block:")
print(old_block)

new_block = """return '<tr>' +
               '<td style="font-weight:bold; cursor:pointer; color:' + color + ';" onclick="openGraphicTab(\\'' + s.symbol + '\\')">' + rankBadge + ' ' + sym + '</td>' +
               '<td style="font-weight:600; color:' + color + ';">\\u20BA' + s.price.toFixed(2) + '</td>' +
               '<td style="color:' + color + '; font-weight:bold;">' + sign + s.change.toFixed(2) + '%</td>' +
               '<td style="color:var(--text-muted);">' + volTLM + '</td>' +
               '<td style="color:var(--text-muted);">' + volLotM + '</td>' +
               '<td style="color:' + color + '; font-weight:bold;">' + relVolText + '</td>' +
               '<td>' + scoreBadge + '</td>' +
               '<td>' + actionBtns + '</td>' +
               '</tr>';"""

code = code[:ret_start] + new_block + code[ret_end:]

with open("ui/app.js", "w", encoding="utf-8") as f:
    f.write(code)
print("Successfully patched renderSuper12Table!")
