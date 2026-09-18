# -*- coding: utf-8 -*-
import re

with open('ui/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Eski tabloyu kaldir
old_table = r'''    <!-- TUM HISSELER TABLOSU -->
    <div class="card glass-panel" style="margin: 1rem 0; border:1px solid rgba(255,255,255,0.1);">
        <div class="card-header"><i class="fa-solid fa-list"></i> Tm Hisseler (Gnlk Deiim)</div>
        <div class="table-scroll-wrapper" style="max-height: 400px; overflow-y: auto;">
            <table>
                <thead>
                    <tr>
                        <th>Hisse</th>
                        <th>Fiyat</th>
                        <th>Deiim \(%\)</th>
                        <th>Hacim</th>
                        <th>Saat</th>
                    </tr>
                </thead>
                <tbody id="tb-all-stocks-home">
                </tbody>
            </table>
        </div>
    </div>'''
content = re.sub(old_table, "", content, flags=re.DOTALL)

# 2. Yeni Modal Ekle (Tavan Karnesi modal'inin altina veya ustune)
new_modal = r'''
<!-- TUM HISSELER MODAL -->
<div id="all-stocks-modal" class="modal">
    <div class="modal-content" style="max-width:600px; max-height:85vh; display:flex; flex-direction:column;">
        <span class="close-btn" onclick="document.getElementById('all-stocks-modal').style.display='none'">&times;</span>
        <h2 style="margin-bottom:1rem; color:var(--accent-blue);"><i class="fa-solid fa-list"></i> Tm Hisseler (Gnlk Deiim)</h2>
        <div class="table-scroll-wrapper" style="flex:1; overflow-y:auto; border-radius:8px; border:1px solid rgba(255,255,255,0.1);">
            <table class="data-table" style="width:100%;">
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
</div>
'''
if "all-stocks-modal" not in content:
    content = content.replace("<!-- TAVAN KARNESI MODAL -->", new_modal + "\n<!-- TAVAN KARNESI MODAL -->")

# 3. Butonu Pill Tabs'e ekle
new_btn = r'''                  <button type="button" class="pill-btn" onclick="document.getElementById('all-stocks-modal').style.display='block'" style="background:linear-gradient(135deg, rgba(59,130,246,0.25), rgba(37,99,235,0.25)); color:#60a5fa; border:1px solid rgba(59,130,246,0.5); padding:7px 15px; border-radius:20px; font-weight:700; font-size:0.85rem; white-space:nowrap; cursor:pointer; display:flex; align-items:center; gap:6px;">
                      <i class="fa-solid fa-list" style="color:#3b82f6;"></i> Y" Tm Hisseler Listesi
                  </button>'''
if "all-stocks-modal" not in content and "Tm Hisseler Listesi" not in content:
    pass # yukarida eklendi, butonu da ekleyelim
content = content.replace('<!-- PILL TABS BITISI / VEYA EKLENECEK YER, regex kullanmiyorum direkt Tavan karnesi butonunun oncesine koyalim -->', '')

# Tavan karnesi butonunun hemen ustune ekleyelim
search_str = r'''                  <button type="button" class="pill-btn" onclick="openTavanAuditModal()"'''
content = content.replace(search_str, new_btn + "\n" + search_str)

with open('ui/index.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("UI_MODAL_YAZILDI")
