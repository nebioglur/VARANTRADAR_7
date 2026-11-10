# -*- coding: utf-8 -*-
with open("ui/app.js", "r", encoding="utf-8") as f:
    code = f.read()

bad_block = """                    card.innerHTML = `
                    <div style="position:absolute; top:0; right:0; background:#10b981; color:#fff; font-size:0.7rem; font-weight:800; padding:3px 10px; border-bottom-left-radius:8px; letter-spacing:1px;">✅ GİR</div>
                    <div style="font-size:1.2rem; font-weight:800; color:#10b981; margin-bottom:0.75rem;">${d.symbol}</div>"""

# Wait, the exact string in the file has different spacing and characters. Let's find it dynamically.
import re
match = re.search(r'(card\.innerHTML\s*=\s*`[^`]*?<div[^>]*?>\$\{d\.symbol\}</div>)', code)
if match:
    # We want to add price right after the symbol div.
    full_str = match.group(1)
    
    # We need to construct the price HTML
    # We can use d.price and d.change_pct
    price_html = """
                      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.75rem; padding-bottom:0.5rem; border-bottom:1px solid rgba(255,255,255,0.05);">
                          <div style="font-size:1.4rem; font-weight:700; color:var(--text-main);">₺${(d.price || 0).toFixed(2)}</div>
                          <div style="font-size:0.9rem; font-weight:bold; color:${(d.change_pct || 0) > 0 ? 'var(--accent-green)' : ((d.change_pct || 0) < 0 ? 'var(--accent-red)' : 'var(--text-muted)')};">${(d.change_pct || 0) > 0 ? '+' : ''}${(d.change_pct || 0).toFixed(2)}%</div>
                      </div>"""
    
    new_str = full_str + price_html
    code = code.replace(full_str, new_str)
    
    with open("ui/app.js", "w", encoding="utf-8") as f:
        f.write(code)
    print("Patched V8 enter card successfully.")
else:
    print("Could not find the V8 enter card HTML block!")
