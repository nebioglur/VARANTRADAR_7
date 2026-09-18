# -*- coding: utf-8 -*-
with open('services/notification_manager.py', 'r', encoding='utf-8') as f:
    content = f.read()

vip_list_str = 'VIP_SYMBOLS = [s + ".IS" for s in ["THYAO", "TUPRS", "ISCTR", "AKBNK", "YKBNK", "GARAN", "SAHOL", "KCHOL", "SISE", "EREGL", "BIMAS", "ASELS", "ENKAI", "SASA", "HEKTS", "FROTO", "TOASO", "TCELL", "TTKOM", "PETKM", "KOZAA", "KOZAL", "KRDMD", "ODAS", "ASTOR", "TAVHL", "PGSUS", "ENJSA", "GWIND", "ALARK", "DOHOL", "SOKM", "MGROS", "VAKBN", "HALKB"]]'

# class basina VIP listesi
content = content.replace("class NotificationManager:", vip_list_str + "\n\nclass NotificationManager:")

# filter in send_tavan_alert
content = content.replace("def send_tavan_alert(cls, symbol, msg_override=None):", "def send_tavan_alert(cls, symbol, msg_override=None):\n        if symbol not in VIP_SYMBOLS: return")

# filter in send_radar_alert
content = content.replace("def send_radar_alert(cls, symbol, data):", "def send_radar_alert(cls, symbol, data):\n        if symbol not in VIP_SYMBOLS: return")

# filter in send_1h_opportunity_alert
content = content.replace("def send_1h_opportunity_alert(cls, symbol, breakout_data):", "def send_1h_opportunity_alert(cls, symbol, breakout_data):\n        if symbol not in VIP_SYMBOLS: return")

# filter in send_5m_rsi_alert
content = content.replace("def send_5m_rsi_alert(cls, symbol, data):", "def send_5m_rsi_alert(cls, symbol, data):\n        if symbol not in VIP_SYMBOLS: return")

# filter in send_simulation_trade_alert
content = content.replace("def send_simulation_trade_alert(cls, trade):", "def send_simulation_trade_alert(cls, trade):\n        if trade.get('symbol') not in VIP_SYMBOLS: return")

# Dag Kekligi metinlerini duzelt
content = content.replace("Dað Kekliði Tavan Adayý", "VIP TAVAN ADAYI")
content = content.replace("Dað Kekliði Erken Fýrsat", "VIP ERKEN FIRSAT")

with open('services/notification_manager.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("PATCH_NOTIF_FINAL_OK")
