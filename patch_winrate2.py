# -*- coding: utf-8 -*-
with open('services/win_rate_engine.py', 'r', encoding='utf-8') as f:
    content = f.read()

import re
content = re.sub(
    r'("desc": f"~6\.2x.*?"\s*\}\s*\]\s*,)\s*"recent_completed_signals":',
    r'\g<1>\n                "daily_breakdown": daily_breakdown,\n                "recent_completed_signals":',
    content,
    flags=re.DOTALL
)

with open('services/win_rate_engine.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("WINRATE RE YAZILDI")
