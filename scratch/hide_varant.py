import sys
with open('ui/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Hide Varant menu buttons
s1 = '<button type="button" class="pill-btn" onclick="switchTab(\'warrants-tab\', this)"><i class="fa-solid fa-layer-group"></i> VARANT</button>'
content = content.replace(s1, '<!-- ' + s1 + ' -->')

s2 = '<button type="button" class="indicator-dot" onclick="switchTab(\'warrants-tab\', document.querySelector(\'.pill-btn:nth-child(5)\'))"><i class="fa-solid fa-layer-group"></i> VARANT</button>'
content = content.replace(s2, '<!-- ' + s2 + ' -->')

# 2. Hide Ahlatci Varant Stat Card
import re
content = re.sub(r'<div class="stat-card" style="border-color: rgba\(168, 85, 247, 0\.2\);">\s*<div><i class="fa-solid fa-building-columns"></i> AHLATCI VARANT ORT\. KÂR</div>', 
                 '<div class="stat-card" style="border-color: rgba(168, 85, 247, 0.2); display: none;">\n                                <div><i class="fa-solid fa-building-columns"></i> AHLATCI VARANT ORT. KÂR</div>', 
                 content)

with open('ui/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("Done hiding Varant elements")
