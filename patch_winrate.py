# -*- coding: utf-8 -*-
with open('services/win_rate_engine.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_ret = '''                        "desc": f"~6.2x kaldıraçlı varant getirisi ortalaması"
                    }
                ],
                "recent_completed_signals": recent_signals'''
new_ret = '''                        "desc": f"~6.2x kaldıraçlı varant getirisi ortalaması"
                    }
                ],
                "daily_breakdown": daily_breakdown,
                "recent_completed_signals": recent_signals'''

content = content.replace(old_ret, new_ret)

with open('services/win_rate_engine.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("WINRATE YAZILDI")
