# -*- coding: utf-8 -*-
with open('server.py', 'r', encoding='utf-8') as f:
    text = f.read()

import re

old_sleep = "time.sleep(15 * 60) # Hizlandirilmis guncelleme, ban riskine karsi 15 dk"

new_sleep = """# Kullanici ozel kural: 10:00'da kesin, 17:58'de kesin, arada 10 dk aralikla
        def get_next_run_seconds():
            import datetime
            now = datetime.datetime.now()
            t_10 = now.replace(hour=10, minute=0, second=0, microsecond=0)
            t_1758 = now.replace(hour=17, minute=58, second=0, microsecond=0)
            
            if now < t_10:
                return (t_10 - now).total_seconds()
            
            if now < t_1758:
                return min(600.0, (t_1758 - now).total_seconds())
                
            t_tomorrow_10 = t_10 + datetime.timedelta(days=1)
            return (t_tomorrow_10 - now).total_seconds()
            
        sleep_secs = get_next_run_seconds()
        print(f"[BACKGROUND] Sradaki tarama icin {int(sleep_secs)} saniye bekleniyor... (Akilli Zamanlayici: 10:00-17:58)")
        time.sleep(sleep_secs)"""

text = text.replace(old_sleep, new_sleep)

with open('server.py', 'w', encoding='utf-8') as f:
    f.write(text)

print("TIMER PATCH OK")
