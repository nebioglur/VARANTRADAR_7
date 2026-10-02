# -*- coding: utf-8 -*-
with open('ui/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

old_html = '''                <button type="button" class="pill-btn" onclick="filterRadarGrid('radar-card-5', this)" style="background:rgba(30,41,59,0.8); color:var(--text-muted); border:1px solid rgba(255,255,255,0.1); padding:7px 15px; border-radius:20px; font-weight:700; font-size:0.85rem; white-space:nowrap; cursor:pointer; display:flex; align-items:center; gap:6px;">
                    <i class="fa-solid fa-arrow-trend-down" style="color:var(--accent-red);"></i> Düşenler
                </button>
            </div>'''
new_html = old_html + '''

            <!-- TUM HISSELER TABLOSU -->
            <div class="card glass-panel" style="grid-column: 1 / -1; margin-bottom:1rem; border:1px solid rgba(255,255,255,0.1);">
                <div class="card-header"><i class="fa-solid fa-list"></i> Tüm Hisseler (Günlük Değişim)</div>
                <div class="table-scroll-wrapper" style="max-height: 400px; overflow-y: auto;">
                    <table>
                        <thead>
                            <tr>
                                <th>Hisse</th>
                                <th>Fiyat</th>
                                <th>Değişim (%)</th>
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
content = content.replace(old_html, new_html)
with open('ui/index.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("UI YAZILDI")
