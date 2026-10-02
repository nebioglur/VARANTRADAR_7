import sys

with open('ui/index.html', 'r', encoding='utf-8') as f:
    c = f.read()

target = '<p style="margin:0.5rem 0 0 0; color:var(--text-muted); font-size:0.95rem;">Tüm BIST hisseleri taranarak kategorize edilmektedir.</p>'

regime_html = """<p style="margin:0.5rem 0 0 0; color:var(--text-muted); font-size:0.95rem;">Tüm BIST hisseleri taranarak kategorize edilmektedir.</p>
                
                <div style="margin-top:15px; padding:12px; background:var(--bg-secondary); border-radius:8px; border:1px solid rgba(255,255,255,0.05); display:inline-block;">
                    <div style="font-size:0.75rem; color:var(--text-muted); margin-bottom:5px;"><i class="fa-solid fa-compass"></i> PİYASA YÖNÜ & NAKİT KOKPİTİ (BIST100)</div>
                    <div id="shield-status" style="font-weight:bold; font-size:1.1rem; color:var(--text-main);">
                        <i class="fa-solid fa-spinner fa-spin"></i> Hesaplanıyor...
                    </div>
                </div>"""

c = c.replace(target, regime_html)

with open('ui/index.html', 'w', encoding='utf-8') as f:
    f.write(c)

print("Added shield-status to index.html")
