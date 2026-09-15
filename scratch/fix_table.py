import re

for filename in ['ui/app.js', 'live_app.js']:
    with open(filename, 'r', encoding='utf-8') as f:
        content = f.read()

    # The buggy string contains 8 td tags
    old_tr = """<td><i class="fa-regular fa-calendar" style="color:var(--text-muted);"></i> ${h.date}</td>
<td>${h.total_signals}</td>
<td style="color:var(--accent-green); font-weight:bold;">${h.hit_ceiling} Tavan (%${h.tavan_rate})</td>
<td style="color:var(--accent-blue); font-weight:bold;">${h.total_candidates || h.total_signals || 0}</td>
<td style="color:var(--accent-green); font-weight:bold;">${h.hit_ceiling_count || h.hit_ceiling || 0} Tavan (%${h.hit_ceiling_pct || h.tavan_rate || 0})</td>
<td style="color:var(--accent-blue); font-weight:bold;">${h.hit_plus5_count || h.hit_plus5 || 0} Adet (%${h.hit_plus5_pct || h.plus5_rate || 0})</td>
<td style="color:var(--accent-yellow); font-weight:bold;">+%${avgMax.toFixed(2)}</td>
<td style="color:${closeColor}; font-weight:bold;">${closeSign}%${avgClose.toFixed(2)}</td>"""

    new_tr = """<td><i class="fa-regular fa-calendar" style="color:var(--text-muted);"></i> ${h.date}</td>
<td>${h.total_candidates || h.total_signals || 0}</td>
<td style="color:var(--accent-green); font-weight:bold;">${h.hit_ceiling_count || h.hit_ceiling || 0} Tavan (%${h.hit_ceiling_pct || h.tavan_rate || 0})</td>
<td style="color:var(--accent-blue); font-weight:bold;">${h.hit_plus5_count || h.hit_plus5 || 0} Adet (%${h.hit_plus5_pct || h.plus5_rate || 0})</td>
<td style="color:var(--accent-yellow); font-weight:bold;">+%${avgMax.toFixed(2)}</td>
<td style="color:${closeColor}; font-weight:bold;">${closeSign}%${avgClose.toFixed(2)}</td>"""

    content = content.replace(old_tr, new_tr)
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(content)
print("Fixed table columns in js")
