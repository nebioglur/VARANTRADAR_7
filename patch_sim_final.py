# -*- coding: utf-8 -*-
import re

with open('services/simulation_engine.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. 17:50 KAPANISINI DUZELT VE TELEGRAM EKLE
old_eod = r"(if close_open_now:\s*trade\['status'\] = 'CLOSED'.*?trade\['exit_reason'\] = )([^\n]+)"
new_eod = r"\1'SEANS SONU NAKITE GECIS (17:50)'\n                    from services.notification_manager import notif\n                    notif.send_simulation_trade_alert(sym, 'SAT (GUN SONU)', close, str(last_time), trade['pnl_pct'], '17:50 Otomatik Kapanis')"
content = re.sub(old_eod, new_eod, content, flags=re.DOTALL)

# 2. AL ISLEMLERINE TELEGRAM EKLE (NORMAL + REENTRY)
# Normal AL
old_al1 = r"('is_reentry': False,.*?)\}\)"
new_al1 = r"\1})\n                from services.notification_manager import notif\n                notif.send_simulation_trade_alert(sym, 'AL', entry_price, str(current_time), None, 'Sistem AL verdi')"
content = re.sub(old_al1, new_al1, content, flags=re.DOTALL)

# Reentry AL
old_al2 = r"('is_reentry': True,.*?)\}\)"
new_al2 = r"\1})\n                    from services.notification_manager import notif\n                    notif.send_simulation_trade_alert(sym, 'AL (Yeniden)', entry_price, str(current_time), None, 'Yeniden Giris')"
content = re.sub(old_al2, new_al2, content, flags=re.DOTALL)

# 3. YARIM KAR AL (TP1) TELEGRAM EKLE
old_tp1 = r"(trade\['shares'\] = remaining_shares.*?trade\['scaled_out'\] = True)"
new_tp1 = r"\1\n                    from services.notification_manager import notif\n                    notif.send_simulation_trade_alert(sym, 'KAR AL (TP1)', tp1_price, str(current_time), pnl_pct, 'TP1 Hedefi Geldi')"
content = re.sub(old_tp1, new_tp1, content, flags=re.DOTALL)

# 4. STOP OLDU TELEGRAM EKLE (Aslında SAT yazmıştık, onu da güncelleyelim)
# notif.send_simulation_trade_alert(sym, "SAT", sell_price, str(current_time), trade['pnl_pct'], reason) -> SAT (STOP) veya SAT (KAR AL)
old_sat = r"notif\.send_simulation_trade_alert\(sym, \"SAT\", sell_price, str\(current_time\), trade\['pnl_pct'\], reason\)"
new_sat = r"notif.send_simulation_trade_alert(sym, 'SAT', sell_price, str(current_time), trade['pnl_pct'], reason)"
content = content.replace(old_sat, new_sat)

with open('services/simulation_engine.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("SIMULATION_PATCH_OK")
