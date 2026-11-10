# -*- coding: utf-8 -*-
from services.live_trade_monitor import open_position

ok, msg = open_position(
    "HRKET",
    price=8.48,
    qty=11759,
    tp_price=8.96,
    sl_price=8.28,
    trailing=True,
    owner="test_owner"
)
print("OK:", ok)
print("MSG:", msg)
