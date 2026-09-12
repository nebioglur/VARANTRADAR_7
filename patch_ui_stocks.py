# -*- coding: utf-8 -*-
with open('ui/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# PILL TABS div'i bitimine ekle
import re
new_html = r'''            </div>

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
content = re.sub(r'(<!-- \?\? MOBL & MASAST HIZLI KATEGOR FLTRE HAPLARI \(PILL TABS\) -->.*?</div>\s*</div>)', r'\g<1>\n' + new_html, content, flags=re.DOTALL)

with open('ui/index.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("UI YAZILDI")
