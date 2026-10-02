# -*- coding: utf-8 -*-
with open('ui/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

nav_target = 'href="/#guide"'
if nav_target in text:
    lines = text.split('\n')
    new_lines = []
    for line in lines:
        new_lines.append(line)
        if nav_target in line and 'nav-btn' in line:
            new_lines.append('              <a class="nav-btn" href="/#super12" onclick="return navClick(event, \'super12\', this)" style="background: linear-gradient(135deg, #FFD700, #F59E0B); color: #000; font-weight: 800; border: 1px solid #F59E0B; box-shadow: 0 0 10px rgba(245, 158, 11, 0.4);"><i class="fa-solid fa-crown"></i> SUPER_12</a>')
    text = '\n'.join(new_lines)

wrapper_target = '<div id="guide-wrapper"'
if wrapper_target in text:
    tab_html = '''
<div id="super12-wrapper" class="main-wrapper" style="display:none; max-width:1200px; margin:0 auto; padding:2rem; color:var(--text-main);">
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:1.5rem;">
        <h2 style="color:#F59E0B; margin:0;"><i class="fa-solid fa-crown"></i> SUPER 12 (Yapay Zeka & Radar Ortak Secimi)</h2>
        <span style="background: rgba(245, 158, 11, 0.1); color: #F59E0B; border: 1px solid #F59E0B; padding: 4px 12px; border-radius: 20px; font-weight: 700; font-size: 0.85rem;"><i class="fa-solid fa-bolt"></i> En Yuksek Skorlu 12 Hisse</span>
    </div>
    
    <div class="card" style="padding:1rem;">
        <div class="table-responsive">
            <table class="data-table" style="width:100%; text-align:left;">
                <thead>
                    <tr>
                        <th>Hisse</th>
                        <th>Fiyat</th>
                        <th>Degisim</th>
                        <th>Hacim(TL)</th>
                        <th>Hacim(Lot)</th>
                        <th>Hacim Gucu %</th>
                        <th>Tavan Skoru</th>
                        <th>Islem</th>
                    </tr>
                </thead>
                <tbody id="tb-super12-stocks">
                    <tr><td colspan="8" style="text-align:center; padding:2rem;">Veriler hesaplaniyor...</td></tr>
                </tbody>
            </table>
        </div>
    </div>
</div>
'''
    text = text.replace(wrapper_target, tab_html + '\n' + wrapper_target)

with open('ui/index.html', 'w', encoding='utf-8') as f:
    f.write(text)
print("SUPER12 HTML PATCHED")
