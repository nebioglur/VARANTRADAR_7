# -*- coding: utf-8 -*-
with open("ui/app.js", "r", encoding="utf-8") as f:
    code = f.read()

anchor = "let intraColor = s.intra_change > 0 ? 'var(--accent-green)' : (s.intra_change < 0 ? 'var(--accent-red)' : 'var(--text-muted)');"
parts = code.split(anchor)

if len(parts) == 3:
    print("Found 2 occurrences of the block as expected.")
    # The first occurrence (index 1) is renderAllStocksTable() - KEEP AS IS.
    # The second occurrence (index 2) is renderSuper12Table() - MODIFY IT.
    
    chunk2 = parts[2]
    # The chunk currently looks like:
    # \n\n        return '<tr>' + ...
    # We need to replace it.
    
    end_idx = chunk2.find("</tr>';") + len("</tr>';")
    before = chunk2[:end_idx]
    after = chunk2[end_idx:]
    
    new_before = """
        return '<tr>' +
               '<td style="font-weight:bold; cursor:pointer; color:' + color + ';" onclick="openGraphicTab(\\'' + s.symbol + '\\')">' + rankBadge + ' ' + sym + '</td>' +
               '<td style="font-weight:600; color:' + color + ';">\\u20BA' + s.price.toFixed(2) + '</td>' +
               '<td style="color:' + color + '; font-weight:bold;">' + sign + s.change.toFixed(2) + '%</td>' +
               '<td style="color:var(--text-muted);">' + volTLM + '</td>' +
               '<td style="color:var(--text-muted);">' + volLotM + '</td>' +
               '<td style="color:' + color + '; font-weight:bold;">' + relVolText + '</td>' +
               '<td>' + scoreBadge + '</td>' +
               '<td>' + actionBtns + '</td>' +
               '</tr>';"""
               
    # Let's also remove intraSign and intraColor definitions from the end of part 1 to avoid unused vars
    # But leaving them is harmless.
    
    code = parts[0] + anchor + parts[1] + anchor + new_before + after
    with open("ui/app.js", "w", encoding="utf-8") as f:
        f.write(code)
    print("Fixed!")
else:
    print(f"Expected 2 occurrences, found {len(parts)-1}")

