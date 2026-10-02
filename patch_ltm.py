with open("services/live_trade_monitor.py", "r", encoding="utf-8") as f:
    text = f.read()

import re

old_block = r"def close_position\(pos_id.*?return True, msg"

new_func = """def close_position_by_symbol(symbol, price=None, reason="MANUEL KAPATMA", owner=None):
    \"\"\"Belirtilen semboldeki acik pozisyonlari kapatir.\"\"\"
    conn = get_connection()
    c = conn.cursor()
    owner = owner or DEFAULT_OWNER
    c.execute("SELECT id FROM live_positions WHERE symbol=? AND status='OPEN' AND owner=?", (symbol, owner))
    rows = c.fetchall()
    
    if not rows:
        conn.close()
        return False, f"{symbol} icin acik pozisyon bulunamadi."
        
    success_count = 0
    msgs = []
    conn.close()
    
    for r in rows:
        ok, msg = close_position(r["id"], price=price, reason=reason, owner=owner)
        if ok:
            success_count += 1
        msgs.append(msg)
        
    if success_count > 0:
        return True, f"{success_count} adet {symbol} pozisyonu kapatildi."
    return False, " | ".join(msgs)
"""

# Append it before get_terminal_state
text = text.replace("def get_terminal_state", new_func + "\n\ndef get_terminal_state")

with open("services/live_trade_monitor.py", "w", encoding="utf-8") as f:
    f.write(text)

print("LTM PATCH DONE")
