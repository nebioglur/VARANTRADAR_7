with open("services/live_trade_monitor.py", "r", encoding="utf-8") as f:
    text = f.read()

import re

old_block = r"def monitor_once\(\):\s*\"\"\"Acik pozisyonlari tarar, akilli TP/SL/trailing kurallarini uygular.\"\"\""

new_block = """def monitor_once():
    \"\"\"Acik pozisyonlari tarar, akilli TP/SL/trailing kurallarini uygular.\"\"\"
    # Piyasa saatleri kontrolu (10:00 - 18:15 arasi calisir).
    # Pre-market veya kapanis sonrasi yanlis/gecikmeli fiyatlarla stop patlamasin!
    from datetime import datetime
    now = datetime.now()
    if now.hour < 10 or (now.hour == 18 and now.minute > 15) or now.hour > 18:
        return {"checked": 0, "closed": [], "msg": "Piyasa kapali (islem saati disi)"}
"""

text = re.sub(old_block, new_block, text)

with open("services/live_trade_monitor.py", "w", encoding="utf-8") as f:
    f.write(text)

print("PATCH HOURS DONE")
