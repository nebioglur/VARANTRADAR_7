# -*- coding: utf-8 -*-
with open('ui/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Navbar'daki calismayan Butonu kaldiralim
import re
content = re.sub(r'<a class="nav-btn" href="javascript:void\(0\)" onclick="document\.getElementById\(\'all-stocks-modal\'\).*?</a>', '', content, flags=re.DOTALL)

# 2. Modalin kendisini (HTML'in en altindan) kaldiralim (gerek yok artik, kart olacak)
content = re.sub(r'<!-- TUM HISSELER MODAL -->.*?<div id="all-stocks-modal" class="modal">.*?</div>\s*</div>\s*</div>', '', content, flags=re.DOTALL)

# 3. Grid Card olarak Arama Kutusunun / Veya "1S Firsat" in filan onune veya arkasina ekleyelim
new_card = r'''
            <!-- TUM HISSELER (GRID KART) -->
            <div class="card glass-panel" id="radar-card-99" style="flex:1; min-width:320px;">
                <h3 style="color:var(--accent-blue); display:flex; justify-content:space-between; align-items:center;">
                    <span><i class="fa-solid fa-list"></i> Tüm Hisseler (BIST)</span>
                    <span style="font-size:0.75rem; background:rgba(59,130,246,0.2); padding:3px 8px; border-radius:12px; color:#60a5fa; border:1px solid rgba(59,130,246,0.3);"><i class="fa-solid fa-arrows-up-down"></i> Scroll</span>
                </h3>
                <div class="table-scroll-wrapper" style="max-height:350px; overflow-y:auto; padding-right:5px; margin-top:10px;">
                    <table class="data-table">
                        <thead>
                            <tr>
                                <th>Hisse</th>
                                <th>Fiyat</th>
                                <th>Deðiþim</th>
                                <th>Hacim</th>
                                <th>Saat</th>
                            </tr>
                        </thead>
                        <tbody id="tb-all-stocks-home">
                        </tbody>
                    </table>
                </div>
            </div>
'''
content = content.replace('<div class="radar-cards-grid" id="radar-cards-grid">', '<div class="radar-cards-grid" id="radar-cards-grid">\n' + new_card)

with open('ui/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
