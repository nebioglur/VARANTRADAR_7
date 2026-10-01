import os

with open("ui/app.js", "r", encoding="utf-8") as f:
    js = f.read()

flow_logic = """        const flowColor = s.hourly_flow === 'Toplanýyor' ? 'var(--accent-green)' : (s.hourly_flow === 'Satýlýyor' ? 'var(--accent-red)' : 'var(--text-muted)');
        
        let flowHtml = s.hourly_flow;
        if (s.hourly_flow === 'Toplanýyor') {
            flowHtml = '<div style="display:flex; flex-direction:column; align-items:center; line-height:1.2;">' +
                       '<div style="display:flex; align-items:flex-end; height:14px; gap:2px; margin-bottom:2px;">' +
                       '<div style="width:4px; height:40%; background:var(--accent-green); opacity:0.5; border-radius:1px;"></div>' +
                       '<div style="width:4px; height:70%; background:var(--accent-green); opacity:0.8; border-radius:1px;"></div>' +
                       '<div style="width:4px; height:100%; background:var(--accent-green); opacity:1.0; border-radius:1px;"></div>' +
                       '</div><span style="font-size:0.75rem;">Toplanýyor</span></div>';
        } else if (s.hourly_flow === 'Satýlýyor') {
            flowHtml = '<div style="display:flex; flex-direction:column; align-items:center; line-height:1.2;">' +
                       '<div style="display:flex; align-items:flex-end; height:14px; gap:2px; margin-bottom:2px;">' +
                       '<div style="width:4px; height:100%; background:var(--accent-red); opacity:1.0; border-radius:1px;"></div>' +
                       '<div style="width:4px; height:70%; background:var(--accent-red); opacity:0.8; border-radius:1px;"></div>' +
                       '<div style="width:4px; height:40%; background:var(--accent-red); opacity:0.5; border-radius:1px;"></div>' +
                       '</div><span style="font-size:0.75rem;">Satýlýyor</span></div>';
        } else if (s.hourly_flow === '-' || !s.hourly_flow) {
            flowHtml = '-';
        }
"""

# Replace flowColor definition
for line in js.split("\n"):
    if "const flowColor =" in line and "hourly_flow" in line:
        js = js.replace(line, flow_logic)
        break

# Replace the td
js = js.replace('<td style="color:${flowColor}; font-weight:bold;">${s.hourly_flow}</td>', '<td style="color:${flowColor}; font-weight:bold;">${flowHtml}</td>')

with open("ui/app.js", "w", encoding="utf-8") as f:
    f.write(js)
