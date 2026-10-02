# -*- coding: utf-8 -*-
with open('services/win_rate_engine.py', 'r', encoding='utf-8') as f:
    content = f.read()

import re

# Ben sunu eklemistim:
# for day in daily_breakdown[:5]:
#    ...
#    daily_breakdown.append(...)
# Ve stats={"daily_breakdown": daily_breakdown, ...}

# Bunun yerine get_performance_stats'i komple eski haline (temiz haline) getirip sonuna dogru kodu ekleyecegim.
# En iyisi, benim attigim "patch_winrate.py" veya "patch_winrate2.py" kalintilarini bulup silmek.

# Veya dogrudan tavan_daily_audit.json formatini 'all_symbols' adinda icine gomelim.
old_block = r"for day in daily_breakdown\[:5\]:.*?recent_completed_signals = \[\]"
# Yerine temiz dongu:
new_block = '''
            proper_daily_breakdown = []
            for date_key, day_data in all_audits.items():
                items = day_data.get("items", [])
                proper_daily_breakdown.append({
                    "date": date_key,
                    "all_symbols": items
                })
            proper_daily_breakdown.sort(key=lambda x: x["date"], reverse=True)
            
            recent_completed_signals = []
'''
content = re.sub(old_block, new_block, content, flags=re.DOTALL)

old_ret = r'"daily_breakdown": daily_breakdown,'
new_ret = r'"daily_breakdown": proper_daily_breakdown,'
content = re.sub(old_ret, new_ret, content)

with open('services/win_rate_engine.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("WINRATE_DUZELTILDI")
