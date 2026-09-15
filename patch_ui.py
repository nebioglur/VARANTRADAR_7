# -*- coding: utf-8 -*-
with open('ui/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Tabloyu ekle: Anasayfaya, muhtemelen "id='home-wrapper'" icine.
old_html = '''        <div id="dashboard-cards" style="display:flex; flex-wrap:wrap; gap:10px; margin-bottom:1rem;">'''
new_html = '''        <div id="dashboard-cards" style="display:flex; flex-wrap:wrap; gap:10px; margin-bottom:1rem;">\n
        <!-- TUM HISSELER TABLOSU -->
        <div class="card glass-panel" style="width:100%; margin-bottom:1rem;">
            <div class="card-header"><i class="fa-solid fa-list"></i> Tm Hisseler (Gnlk Deiim)</div>
            <div class="table-scroll-wrapper" style="max-height: 400px; overflow-y: auto;">
                <table>
                    <thead>
                        <tr>
                            <th>Hisse</th>
                            <th>Fiyat</th>
                            <th>Deiim (%)</th>
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
    f.write(content.replace("Tm Hisseler (Gnlk Deiim)", "Tüm Hisseler (Günlük Değişim)").replace("Deiim (%)", "Değişim (%)"))

print("UI YAZILDI")
