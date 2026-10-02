# -*- coding: utf-8 -*-
import re

with open('ui/app.js', 'r', encoding='utf-8') as f:
    text = f.read()

# Ortak S/R hesaplama kodu (her iki tablo cizim dongusu icine eklenecek)
calc_code = '''
        let p_val = (s.high + s.low + s.price) / 3;
        let dR1 = (2 * p_val) - s.low;
        let dS1 = (2 * p_val) - s.high;
        if (s.price > dR1) dR1 = p_val + (s.high - s.low);
        if (s.price < dS1) dS1 = p_val - (s.high - s.low);
        let hR1 = s.price + (dR1 - s.price) * 0.4;
        let hS1 = s.price - (s.price - dS1) * 0.4;
        
        let dR1_p = s.price > 0 ? ((dR1 - s.price)/s.price)*100 : 0;
        let dS1_p = s.price > 0 ? ((dS1 - s.price)/s.price)*100 : 0;
        let hR1_p = s.price > 0 ? ((hR1 - s.price)/s.price)*100 : 0;
        let hS1_p = s.price > 0 ? ((hS1 - s.price)/s.price)*100 : 0;
        
        let ddCell = '<td style="font-size:0.65rem; line-height:1.2; min-width:140px;">' +
                     '<div style="display:flex; justify-content:space-between; margin-bottom:2px;"><span style="color:var(--text-muted);">S:</span> <span><span style="color:var(--accent-red);">' + hS1.toFixed(2) + '(%'+hS1_p.toFixed(1)+')</span> / <span style="color:var(--accent-green);">' + hR1.toFixed(2) + '(+%'+hR1_p.toFixed(1)+')</span></span></div>' +
                     '<div style="display:flex; justify-content:space-between;"><span style="color:var(--text-muted);">G:</span> <span><span style="color:var(--accent-red);">' + dS1.toFixed(2) + '(%'+dS1_p.toFixed(1)+')</span> / <span style="color:var(--accent-green);">' + dR1.toFixed(2) + '(+%'+dR1_p.toFixed(1)+')</span></span></div>' +
                     '</td>';
'''

# 1. renderAllStocksTable patch
# Bulacagimiz yer: let scoreBadge = 
# Bunun hemen oncesine calc_code'u koyacagiz.
text = re.sub(r'(let scColor = \'#ef4444\';)', calc_code.replace('\\', '\\\\') + r'\n          \1', text)

# 2. HTML td ekleme (renderAllStocksTable - backticks)
# <td style="color:; font-weight:bold;"></td>
text = re.sub(r'(<td style="color:\$\{color\}; font-weight:bold;">\$\{relVolText\}</td>)', r'\1\n                  ', text)

# 3. HTML td ekleme (renderSuper12Table - single quotes ASCII mode)
# '<td style="color:' + color + '; font-weight:bold;">' + relVolText + '</td>' +
text = re.sub(r'(\'<td style="color:\' \+ color \+ \'; font-weight:bold;">\' \+ relVolText \+ \'</td>\' \+)', r'\1\n               ddCell +', text)


with open('ui/app.js', 'w', encoding='utf-8') as f:
    f.write(text)

print("JS DD PATCH OK")
