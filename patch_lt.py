# -*- coding: utf-8 -*-
with open("services/live_trade_monitor.py", "r", encoding="utf-8") as f:
    code = f.read()

bad_block = """    live_price, src = _get_live_price(clean)
    if not live_price or live_price <= 0:
        return False, f"{clean} icin guncel fiyat alinamadi"

    manual_price = _f(price)
    if manual_price is not None:
        entry_price = round(manual_price, 2)
        base_price = entry_price
    else:
        entry_price = round(live_price * 1.0015, 2)  # slipaj
        base_price = live_price"""

good_block = """    manual_price = _f(price)
    if manual_price is not None:
        entry_price = round(manual_price, 2)
        base_price = entry_price
        live_price = entry_price
    else:
        live_price, src = _get_live_price(clean)
        if not live_price or live_price <= 0:
            return False, f"{clean} icin guncel fiyat alinamadi"
        entry_price = round(live_price * 1.0015, 2)  # slipaj
        base_price = live_price"""

if bad_block in code:
    code = code.replace(bad_block, good_block)
    with open("services/live_trade_monitor.py", "w", encoding="utf-8") as f:
        f.write(code)
    print("Patched open_position successfully.")
else:
    print("Could not find bad_block!")
