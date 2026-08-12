import sys

with open('ui/app.js', 'r', encoding='utf-8') as f:
    c = f.read()

old_html = "            <td style=\"color:#facc15; font-weight:800; font-size:0.9rem;\">+ %${d.avg_max_gain_pct}</td>"

new_html = """            <td>
                <div style="font-weight:800; font-size:0.9rem; color:${d.avg_closing_gain_pct >= 0 ? '#10b981' : '#ef4444'}">
                    ${d.avg_closing_gain_pct >= 0 ? '+' : ''}%${d.avg_closing_gain_pct}
                </div>
                <div style="font-size:0.75rem; color:var(--text-muted); margin-top:2px;">Zirve: <span style="color:#facc15">+%${d.avg_max_gain_pct}</span></div>
            </td>"""

if old_html in c:
    c = c.replace(old_html, new_html)
    with open('ui/app.js', 'w', encoding='utf-8') as f:
        f.write(c)
    print('SUCCESS')
else:
    print('FAILED')
