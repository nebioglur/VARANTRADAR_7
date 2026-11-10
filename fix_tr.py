import re

with open("ui/app.js", "r", encoding="utf-8") as f:
    content = f.read()

target = """        let rankBadge = '<span style="display:inline-block; width:30px; text-align:center; color:var(--text-muted); font-size:0.85rem; font-weight:bold; margin-right:5px; background:rgba(0,0,0,0.05); border-radius:4px;">#' + (index+1) + '</span>';
        
        return '<tr>' +
               '<td style="font-weight:bold; cursor:pointer; color:' + color + ';" onclick="openGraphicTab(\\'' + s.symbol + '\\')">' + rankBadge + ' ' + sym + '</td>' +
               '<td style="font-weight:600; color:' + color + ';">\\u20BA' + s.price.toFixed(2) + '</td>' +
               '<td style="color:' + color + '; font-weight:bold;">' + sign + s.change.toFixed(2) + '%</td>' +
               '<td style="color:var(--text-muted);">' + volTLM + '</td>' +
               '<td style="color:var(--text-muted);">' + volLotM + '</td>' +
               '<td style="color:' + color + '; font-weight:bold;">' + relVolText + '</td>' +

               '<td>' + scoreBadge + '</td>' +
               '<td>' + actionBtns + '</td>' +
               '</tr>';
    }).join('');"""

replacement = """        let rankBadge = '<span style="display:inline-block; width:30px; text-align:center; color:var(--text-muted); font-size:0.85rem; font-weight:bold; margin-right:5px; background:rgba(0,0,0,0.05); border-radius:4px;">#' + (index+1) + '</span>';
        let prevClose = s.close || (s.price / (1 + (s.change / 100)));
        let intraSign = s.intra_change > 0 ? '+' : '';
        let intraColor = s.intra_change > 0 ? 'var(--accent-green)' : (s.intra_change < 0 ? 'var(--accent-red)' : 'var(--text-muted)');

        return '<tr>' +
               '<td style="font-weight:bold; cursor:pointer; color:' + color + ';" onclick="openGraphicTab(\\'' + s.symbol + '\\')">' + rankBadge + ' ' + sym + '</td>' +
               '<td style="font-weight:600; color:' + color + ';">\\u20BA' + s.price.toFixed(2) + '</td>' +
               '<td style="color:var(--text-muted);">\\u20BA' + prevClose.toFixed(2) + '</td>' +
               '<td style="color:' + color + '; font-weight:bold;">' + sign + s.change.toFixed(2) + '%</td>' +
               '<td style="color:' + intraColor + '; font-weight:bold;">' + intraSign + (s.intra_change || 0).toFixed(2) + '%</td>' +
               '<td>' + flowHtml + '</td>' +
               '<td style="color:var(--text-muted);">' + volTLM + '</td>' +
               '<td style="color:var(--text-muted);">' + volLotM + '</td>' +
               '<td style="color:' + color + '; font-weight:bold;">' + relVolText + '</td>' +
               '<td>' + scoreBadge + '</td>' +
               '<td>' + actionBtns + '</td>' +
               '</tr>';
    }).join('');"""

if target in content:
    content = content.replace(target, replacement)
    with open("ui/app.js", "w", encoding="utf-8") as f:
        f.write(content)
    print("REPLACED!")
else:
    print("TARGET NOT FOUND!")
