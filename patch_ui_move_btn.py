# -*- coding: utf-8 -*-
with open('ui/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Eski pill-btn'i kaldiralim
old_btn = r'''<button type="button" class="pill-btn" onclick="document.getElementById('all-stocks-modal').style.display='block'" style="background:linear-gradient(135deg, rgba(59,130,246,0.25), rgba(37,99,235,0.25)); color:#60a5fa; border:1px solid rgba(59,130,246,0.5); padding:7px 15px; border-radius:20px; font-weight:700; font-size:0.85rem; white-space:nowrap; cursor:pointer; display:flex; align-items:center; gap:6px;">
                    <i class="fa-solid fa-list" style="color:#3b82f6;"></i> Tüm Hisseler Listesi
                </button>'''
# Windows'da char encoding sorunu olabilir, regex ile silelim
import re
content = re.sub(r'\s*<button type="button" class="pill-btn" onclick="document\.getElementById\(\'all-stocks-modal\'\)\.style\.display=\'block\'".*?</button>', '', content, flags=re.DOTALL)

# Nav-btn olarak NASIL KULLANILIR yanina ekleyelim
nav_btn = r'''<a class="nav-btn" href="javascript:void(0)" onclick="document.getElementById('all-stocks-modal').style.display='block'" style="color:#60a5fa; border:1px solid rgba(59,130,246,0.4);"><i class="fa-solid fa-list"></i> TM HSSELER</a>
            <a class="nav-btn" href="/#guide"'''
content = re.sub(r'<a class="nav-btn" href="/#guide"', nav_btn, content)

with open('ui/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("UI_BUTTON_MOVED")
