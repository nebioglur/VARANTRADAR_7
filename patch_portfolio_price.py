# -*- coding: utf-8 -*-
import codecs

with codecs.open('ui/index.html', 'r', 'utf-8') as f:
    html = f.read()

# 1. lt-allocation varsayilan degerini (2000) kaldir
html = html.replace('value="2000" min="100"', '')

# 2. lt-price inputu ekle (ADET oncesine)
old_qty_div = '''<div style="flex:0 0 84px;">
                    <label style="font-size:0.7rem; color:var(--text-muted); display:block; margin-bottom:3px;">ADET</label>
                    <input id="lt-qty" type="text" inputmode="numeric" min="1" placeholder="?" onblur="normNumField('lt-qty', {integer:true})" style="width:100%; background:var(--bg-base); border:1px solid var(--border-color); color:var(--text-main); border-radius:6px; padding:7px 10px; font-size:0.9rem;">
                </div>'''
# Eger '?' isareti sorun olursa diye daha esnek bi arama yapalim.
import re
html = re.sub(r'<div style="flex:0 0 84px;">\s*<label[^>]*>ADET</label>\s*<input id="lt-qty"[^>]*>\s*</div>', 
    '''<div style="flex:0 0 84px;">
                    <label style="font-size:0.7rem; color:var(--text-muted); display:block; margin-bottom:3px;">FÝYAT(?)</label>
                    <input id="lt-price" type="text" inputmode="decimal" min="0" placeholder="Anlýk" onblur="normNumField('lt-price')" style="width:100%; background:var(--bg-base); border:1px solid var(--border-color); color:var(--text-main); border-radius:6px; padding:7px 10px; font-size:0.9rem;">
                </div>
                <div style="flex:0 0 84px;">
                    <label style="font-size:0.7rem; color:var(--text-muted); display:block; margin-bottom:3px;">ADET</label>
                    <input id="lt-qty" type="text" inputmode="numeric" min="1" placeholder="" onblur="normNumField('lt-qty', {integer:true})" style="width:100%; background:var(--bg-base); border:1px solid var(--border-color); color:var(--text-main); border-radius:6px; padding:7px 10px; font-size:0.9rem;">
                </div>''', html)

with codecs.open('ui/index.html', 'w', 'utf-8') as f:
    f.write(html)
print("HTML PATCHED")
