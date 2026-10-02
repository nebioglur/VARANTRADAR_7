# -*- coding: utf-8 -*-
with open('services/simulation_engine.py', 'r', encoding='utf-8') as f:
    text = f.read()

import re

# Satislardaki notif çagrilari (line 484 civari)
# notif.send_simulation_trade_alert(sym, "SAT", sell_price, str(current_time), trade['pnl_pct'], reason)
text = re.sub(r'notif\.send_simulation_trade_alert\(sym, "SAT", sell_price, str\(current_time\), trade\[\'pnl_pct\'\], reason\)', 
              r'from services.telegram_bot import notify_sim_trade\n                    notify_sim_trade(sym, "SAT", sell_price, trade["pnl_pct"], reason, str(current_time)[:10])', text)

# Alislardaki notif çagrilari
text = re.sub(r'from services\.notification_manager import notif\s*notif\.send_simulation_trade_alert\(sym, \'AL\', entry_price, str\(current_time\), None, \'Sistem AL verdi\'\)', 
              r'from services.telegram_bot import notify_sim_trade\n                notify_sim_trade(sym, "AL", entry_price, 0.0, "Sistem AL verdi", str(current_time)[:10])', text)

# Yeniden Giris notif çagrilari
text = re.sub(r'from services\.notification_manager import notif\s*notif\.send_simulation_trade_alert\(sym, \'AL \(Yeniden\)\', entry_price, str\(current_time\), None, \'Yeniden Giris\'\)', 
              r'from services.telegram_bot import notify_sim_trade\n                    notify_sim_trade(sym, "AL (Yeniden)", entry_price, 0.0, "Yeniden Giris", str(current_time)[:10])', text)

# Seans Sonu Satis notif çagrilari
text = re.sub(r'from services\.notification_manager import notif\s*notif\.send_simulation_trade_alert\(sym, \'SAT \(GUN SONU\)\', close, str\(last_time\), trade\[\'pnl_pct\'\], \'17:50 Otomatik Kapanis\'\)', 
              r'from services.telegram_bot import notify_sim_trade\n                    notify_sim_trade(sym, "SAT (GUN SONU)", close, trade["pnl_pct"], "17:50 Otomatik Kapanis", str(last_time)[:10])', text)

with open('services/simulation_engine.py', 'w', encoding='utf-8') as f:
    f.write(text)
print("SIM NOTIF PATCH OK")
