import re

with open('ui/index.html', 'r', encoding='utf-8') as f:
    c = f.read()

old_html = """                <!-- 5 Dakikalık Kısa Trade Sinyalleri -->
                <div class="card" id="radar-card-2" style="padding:1rem; border:1px solid rgba(59, 130, 246, 0.5); box-shadow: 0 0 15px rgba(59,130,246,0.15);">"""

new_html = """                <!-- UZAK DUR HİSSELERİ (1 Saatlik Negatif Momentum) -->
                <div class="card" id="radar-card-stay-away" style="padding:1rem; border:1px solid rgba(239, 68, 68, 0.5); box-shadow: 0 0 15px rgba(239,68,68,0.15);">
                    <h3 class="card-title" style="font-size:1rem; margin-bottom:0.8rem; color:var(--accent-red);"><i class="fa-solid fa-triangle-exclamation"></i> UZAK DUR HİSSELERİ! <span id="time-stay-away-1h" style="float:right; font-size:0.75rem; font-weight:normal; color:var(--text-muted); margin-top:5px;"></span></h3>
                    <p style="font-size:0.8rem; color:var(--text-muted); margin-bottom:0.5rem; margin-top:-0.5rem;">Sert düşüş sinyali: 1 saatlikte EMA, MACD, RSI ve Momentum SAT veriyor.</p>
                    <div style="max-height:350px; overflow-y:auto;">
                    <table class="data-table" style="width: 100%;">
                        <thead><tr><th>Sembol</th><th>Fiyat</th><th>Şart (X/5)</th><th>Düşüş Sinyali</th><th style="width:60px;"></th></tr></thead>
                        <tbody id="tb-stay-away-1h"><tr><td colspan="5" class="text-muted text-center">Taranıyor...</td></tr></tbody>
                    </table>
                    </div>
                </div>
                
                <!-- 5 Dakikalık Kısa Trade Sinyalleri -->
                <div class="card" id="radar-card-2" style="padding:1rem; border:1px solid rgba(59, 130, 246, 0.5); box-shadow: 0 0 15px rgba(59,130,246,0.15);">"""

if old_html in c:
    c = c.replace(old_html, new_html)
    with open('ui/index.html', 'w', encoding='utf-8') as f:
        f.write(c)
    print('SUCCESS')
else:
    print('FAILED TO FIND HTML')
