# -*- coding: utf-8 -*-
with open('services/win_rate_engine.py', 'r', encoding='utf-8') as f:
    content = f.read()

import re

# Satir 43 civari: all_audits = TavanAuditTracker.load_all_audits()
# Bunun hemen altina proper_daily_breakdown tanimlayacagim.
new_def = '''            all_audits = TavanAuditTracker.load_all_audits()
            proper_daily_breakdown = []
            for date_key, day_data in all_audits.items():
                proper_daily_breakdown.append({
                    "date": date_key,
                    "all_symbols": day_data.get("items", [])
                })
            proper_daily_breakdown.sort(key=lambda x: x["date"], reverse=True)
'''
content = content.replace("            all_audits = TavanAuditTracker.load_all_audits()", new_def)

with open('services/win_rate_engine.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("WINRATE_FIX_YAZILDI")
