import sys

def fix_file(fname):
    with open(fname, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. history variable
    content = content.replace('const history = data.history || [];', 'const history = data.daily_breakdown || data.history || [];')

    # 2. total_closed_positive
    content = content.replace('${summ.total_closed_positive || 0} Adet', '${summ.total_closed_positive || summ.total_hit_plus5 || 0} Adet')
    content = content.replace('(Ort. +%${(summ.avg_positive_close_gain || 0).toFixed(2)})', '(Ort. +%${(summ.avg_positive_close_gain || summ.cumulative_avg_max_gain_pct || 0).toFixed(2)})')

    content = content.replace('${summ.total_closed_negative || 0} Adet', '${summ.total_closed_negative || ((summ.total_candidates_tracked || 0) - (summ.total_hit_plus5 || 0))} Adet')
    content = content.replace('(Ort. ${summ.avg_negative_close_gain < 0 ? \'\' : \'-\' }%${Math.abs(summ.avg_negative_close_gain || 0).toFixed(2)})', '(Ort. %${Math.abs(summ.avg_negative_close_gain || 0).toFixed(2)})')

    content = content.replace('let netPct = summ.net_profit_pct || 0;', 'let netPct = summ.net_profit_pct || summ.cumulative_avg_closing_gain_pct || 0;')

    content = content.replace('(Ort. ${summ.elite_avg_negative_gain < 0 ? \'\' : \'-\' }%${Math.abs(summ.elite_avg_negative_gain || 0).toFixed(2)})', '(Ort. %${Math.abs(summ.elite_avg_negative_gain || 0).toFixed(2)})')

    # 3. Table fields
    content = content.replace('const avgClose = h.avg_closing_gain_pct || h.avg_close_gain || 0;', 'const avgClose = h.avg_closing_gain_pct || h.avg_close_gain || 0;\n                        const avgMax = h.avg_max_gain_pct || h.avg_max_gain || 0;')
    
    # 4. Table Row replacement
    content = content.replace('<td style="color:var(--accent-blue); font-weight:bold;">${h.hit_plus5} Adet (%${h.plus5_rate})</td>', '<td style="color:var(--accent-blue); font-weight:bold;">${h.total_candidates || h.total_signals || 0}</td>\n                            <td style="color:var(--accent-green); font-weight:bold;">${h.hit_ceiling_count || h.hit_ceiling || 0} Tavan (%${h.hit_ceiling_pct || h.tavan_rate || 0})</td>\n                            <td style="color:var(--accent-blue); font-weight:bold;">${h.hit_plus5_count || h.hit_plus5 || 0} Adet (%${h.hit_plus5_pct || h.plus5_rate || 0})</td>')
    
    content = content.replace('+%${h.avg_max_gain.toFixed(2)}', '+%${avgMax.toFixed(2)}')
    content = content.replace('${closeSign}%${h.avg_close_gain.toFixed(2)}', '${closeSign}%${avgClose.toFixed(2)}')

    with open(fname, 'w', encoding='utf-8') as f:
        f.write(content)

fix_file('ui/app.js')
fix_file('live_app.js')
fix_file('varantradar_pro2/ui/app.js')
