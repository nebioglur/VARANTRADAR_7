with open('live_app.js', 'r', encoding='utf-8') as f:
    content = f.read()

old = ' Adet (%)'
new = '</td>\n                            <td style="color:var(--accent-green); font-weight:bold;"> Tavan (%)</td>\n                            <td style="color:var(--accent-blue); font-weight:bold;"> Adet (%)'
content = content.replace(old, new)
content = content.replace('+%', '+%')
content = content.replace('%', '%')
# Fix data.history -> data.daily_breakdown
content = content.replace("const history = data.history || [];", "const history = data.daily_breakdown || data.history || [];")
# Fix net pct fallback
content = content.replace("let netPct = summ.net_profit_pct || 0;", "let netPct = summ.net_profit_pct || summ.cumulative_avg_closing_gain_pct || 0;")

with open('live_app.js', 'w', encoding='utf-8') as f:
    f.write(content)
print('live_app.js Done')
