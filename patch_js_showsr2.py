# -*- coding: utf-8 -*-
import re

with open('ui/app.js', 'r', encoding='utf-8') as f:
    text = f.read()

# I will find everything from 'window.showSR = function' to the end of the file and replace it.
# Because I appended it at the end of the file!
pattern = r'window\.showSR = function\(sym, price, high, low\) \{.*'
if not re.search(pattern, text, re.DOTALL):
    pattern = r'function showSR\(sym, price, high, low\) \{.*'

new_func = '''window.showSR = function(sym, price, high, low) {
    try {
        price = parseFloat(price) || 0;
        high = parseFloat(high) || price;
        low = parseFloat(low) || price;
        let p_val = (high + low + price) / 3.0;
        let dR1 = (2 * p_val) - low;
        let dS1 = (2 * p_val) - high;
        if (price > dR1) dR1 = p_val + (high - low);
        if (price < dS1) dS1 = p_val - (high - low);
        let hR1 = price + (dR1 - price) * 0.4;
        let hS1 = price - (price - dS1) * 0.4;
        
        let dR1_p = price > 0 ? ((dR1 - price)/price)*100 : 0;
        let dS1_p = price > 0 ? ((dS1 - price)/price)*100 : 0;
        let hR1_p = price > 0 ? ((hR1 - price)/price)*100 : 0;
        let hS1_p = price > 0 ? ((hS1 - price)/price)*100 : 0;
        
        let html = <div style="text-align:left; font-size:0.95rem; line-height:1.6; color:var(--text-main);">
            <h3 style="color:var(--accent-blue); margin-top:0; border-bottom:1px solid rgba(255,255,255,0.1); padding-bottom:10px;"><i class="fa-solid fa-crosshairs"></i>  - Seviyeler</h3>
            <p style="margin-bottom:5px; font-weight:bold;">Anl\u0131k Fiyat: \u20BA</p>
            
            <div style="background:rgba(0,0,0,0.2); padding:10px; border-radius:8px; border-left:3px solid var(--accent-yellow); margin-bottom:15px;">
                <b style="color:var(--accent-yellow);"><i class="fa-regular fa-clock"></i> Saatlik (K\u0131sa Vade)</b><br>
                <span style="color:var(--text-muted);">Diren\u00e7:</span> <span style="color:var(--accent-green); font-weight:bold;">\u20BA (+%)</span><br>
                <span style="color:var(--text-muted);">Destek:</span> <span style="color:var(--accent-red); font-weight:bold;">\u20BA (%)</span>
            </div>
            
            <div style="background:rgba(0,0,0,0.2); padding:10px; border-radius:8px; border-left:3px solid var(--accent-purple); margin-bottom:5px;">
                <b style="color:var(--accent-purple);"><i class="fa-regular fa-calendar"></i> G\u00fcnl\u00fck (Pivot)</b><br>
                <span style="color:var(--text-muted);">Diren\u00e7:</span> <span style="color:var(--accent-green); font-weight:bold;">\u20BA (+%)</span><br>
                <span style="color:var(--text-muted);">Destek:</span> <span style="color:var(--accent-red); font-weight:bold;">\u20BA (%)</span>
            </div>
        </div>;
        
        if (typeof Swal !== 'undefined') {
            Swal.fire({
                html: html,
                background: 'var(--bg-base)',
                color: 'var(--text-main)',
                showConfirmButton: true,
                confirmButtonText: 'Kapat',
                confirmButtonColor: '#3b82f6'
            });
        } else {
            alert(sym + " Pivot Seviyeleri\nFiyat: " + price.toFixed(2) + "\nG. Direnc: " + dR1.toFixed(2) + "\nG. Destek: " + dS1.toFixed(2));
        }
    } catch(e) {
        console.error("showSR error:", e);
        alert("Destek/Direnc gosterilirken hata: " + e.message);
    }
};
'''

text = re.sub(pattern, new_func, text, flags=re.DOTALL)

with open('ui/app.js', 'w', encoding='utf-8') as f:
    f.write(text)

print("SHOWSR PATCH 2 OK")
