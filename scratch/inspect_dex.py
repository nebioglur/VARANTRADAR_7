import zipfile

with zipfile.ZipFile('apk/VarantRadarPro.apk', 'r') as z:
    dex = z.read('classes.dex')

print("DEX length:", len(dex))
# Search for strings in DEX
import re
strings = re.findall(rb'[a-zA-Z0-9_\.:/]{4,}', dex)
for s in strings:
    s_str = s.decode('ascii', errors='ignore')
    if any(k in s_str for k in ['http', 'varant', 'Main', 'Web', 'url', 'Url', 'pythonanywhere']):
        print(" ", s_str)
