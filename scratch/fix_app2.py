import sys

def fix_file(fname):
    with open(fname, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. history variable
    content = content.replace('const history = data.history || [];', 'const history = data.daily_breakdown || data.history || [];')

    # 2. total_closed_positive
    content = content.replace('\ Adet', '\ Adet')
    content = content.replace('(Ort. +%\)', '(Ort. +%\)')

    content = content.replace('\ Adet', '\ Adet')
    content = content.replace('(Ort. \%\)', '(Ort. %\)')

    content = content.replace('let netPct = summ.net_profit_pct || 0;', 'let netPct = summ.net_profit_pct || summ.cumulative_avg_closing_gain_pct || 0;')

    content = content.replace('(Ort. \%\)', '(Ort. %\)')

    # 3. Table fields
    content = content.replace('const avgClose = h.avg_closing_gain_pct || h.avg_close_gain || 0;', 'const avgClose = h.avg_closing_gain_pct || h.avg_close_gain || 0;\n                        const avgMax = h.avg_max_gain_pct || h.avg_max_gain || 0;')
    
    # 4. Table Row replacement
    content = content.replace('<td style=\"color:var(--accent-blue); font-weight:bold;\">\ Adet (%\)</td>', '<td style=\"color:var(--accent-blue); font-weight:bold;\">\</td>\\n                            <td style=\"color:var(--accent-green); font-weight:bold;\">\ Tavan (%\)</td>\\n                            <td style=\"color:var(--accent-blue); font-weight:bold;\">\ Adet (%\)</td>')
    
    content = content.replace('+%\', '+%\')
    content = content.replace('\%\', '\%\')

    with open(fname, 'w', encoding='utf-8') as f:
        f.write(content)

fix_file('ui/app.js')
fix_file('live_app.js')
fix_file('varantradar_pro2/ui/app.js')
