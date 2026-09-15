import sys
with open('ui/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Hide Varant nav tab
s1 = '<button class="nav-btn" onclick="switchMainTab(\'varant\', this)"><i class="fa-solid fa-calculator"></i> VARANT</button>'
content = content.replace(s1, '<!-- ' + s1 + ' -->')

# Hide Ahlatci stat card - let's find the stat card div before the text
import re
content = re.sub(r'<div class="stat-card" style="border-color: rgba\(168, 85, 247, 0\.2\);">(\s*<div><i class="fa-solid fa-building-columns"></i> AHLATCI)', 
                 r'<div class="stat-card" style="border-color: rgba(168, 85, 247, 0.2); display: none;">\g<1>', 
                 content, flags=re.IGNORECASE)

with open('ui/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("Replaced!")
