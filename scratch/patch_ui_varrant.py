import os

with open('ui/app.js', 'r', encoding='utf-8') as f:
    text = f.read()

target = '<td style="font-size:0.8rem; color:var(--text-muted); max-width:200px; white-space:normal;">${d.entry_reasons[0] || \'-\'}</td>'
idx = text.find(target)

if idx != -1:
    replace_with = """
                    <td style="font-size:0.8rem; color:var(--text-muted); max-width:200px; white-space:normal;">
                        <div>${d.entry_reasons[0] || '-'}</div>
                        ${d.varrant_info && d.varrant_info.status === 'VARRANT_FOUND' ? 
                          '<div style="margin-top:4px; font-size:0.75rem; color:var(--accent-purple);"><i class="fa-solid fa-bolt"></i> Varant: ' + d.varrant_info.varrant_prefix + ' (Kaldıraç: ~' + d.varrant_info.estimated_leverage + 'x)</div>' 
                          : ''}
                    </td>
    """
    
    text = text.replace(target, replace_with)
    with open('ui/app.js', 'w', encoding='utf-8') as f:
        f.write(text)
    print("UI updated with varrant info")
else:
    print("Target not found")
