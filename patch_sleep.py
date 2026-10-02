# -*- coding: utf-8 -*-
with open('server.py', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace('time.sleep(8 * 60) # Hizlandirilmis guncelleme', 'time.sleep(15 * 60) # Hizlandirilmis guncelleme, ban riskine karsi 15 dk')

with open('server.py', 'w', encoding='utf-8') as f:
    f.write(text)
print("SLEEP UPDATED")
