# -*- coding: utf-8 -*-
with open('server.py', 'r', encoding='utf-8') as f:
    text = f.read()

import re

# Remove the Render block that kills the background scanner
pattern = r'if os\.environ\.get\("RENDER"\):\s*print\("\[BACKGROUND\] Render sunucusunda agir BIST taramasi IP iptali yuzunden kapatildi.*?\s*return'
text = re.sub(pattern, '', text, flags=re.DOTALL)

with open('server.py', 'w', encoding='utf-8') as f:
    f.write(text)
print("RENDER SCANNER ENABLED")
