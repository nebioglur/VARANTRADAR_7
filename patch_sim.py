# -*- coding: utf-8 -*-
with open('services/simulation_engine.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. 17:52 rule (or 17:50) -> The original commit message said "fix: 17:52 sonrasi". 
# So let's check what it is in the file right now.
import re
# 2. Add notif initialization
content = content.replace(
    '''        valid_signals = []\n        for s in signals:''',
    '''        valid_signals = []\n        from services.notification_manager import NotificationManager\n        notif = NotificationManager()\n        for s in signals:'''
)

# 3. Add send_simulation_trade_alert for AL (Initial)
content = content.replace(
    '''                                    'is_reentry': False\n                                })''',
    '''                                    'is_reentry': False\n                                })\n                                notif.send_simulation_trade_alert(sym, "AL", entry_price, str(current_time), reason="Yeni Gün İçi Kırılım")'''
)

# 4. Add send_simulation_trade_alert for AL (Re-entry)
content = content.replace(
    '''                                            'is_reentry': True\n                                        })''',
    '''                                            'is_reentry': True\n                                        })\n                                        notif.send_simulation_trade_alert(sym, "AL", entry_price, str(current_time), reason="Trende Yeniden Giriş (Re-Entry)")'''
)

# 5. Add send_simulation_trade_alert for SAT (TP1)
content = content.replace(
    '''                            'exit_reason': "⚖️ ÇELİK TP1 (YARISI SATILDI)"\n                        })''',
    '''                            'exit_reason': "⚖️ ÇELİK TP1 (YARISI SATILDI)"\n                        })\n                        notif.send_simulation_trade_alert(sym, "SAT (Yarısı)", scale_out_price, str(current_time), (net_profit / buy_vol) * 100, "⚖️ ÇELİK TP1 (YARISI SATILDI)")'''
)

# 6. Add send_simulation_trade_alert for SAT (STOP/TP2)
content = content.replace(
    '''                    completed_trades.append(trade)\n                    \n                    if "STOP" in reason:''',
    '''                    completed_trades.append(trade)\n                    notif.send_simulation_trade_alert(sym, "SAT", sell_price, str(current_time), trade['pnl_pct'], reason)\n                    \n                    if "STOP" in reason:'''
)

# 7. Add send_simulation_trade_alert for SAT (EOD Force Close)
content = content.replace(
    '''                completed_trades.append(trade)\n                current_cash += sell_volume - commission''',
    '''                completed_trades.append(trade)\n                notif.send_simulation_trade_alert(sym, "SAT", close, str(last_time), trade['pnl_pct'], trade['exit_reason'])\n                current_cash += sell_volume - commission'''
)

with open('services/simulation_engine.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("SIM YAZILDI")
