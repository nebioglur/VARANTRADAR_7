# -*- coding: utf-8 -*-
import codecs

with codecs.open('services/live_trade_monitor.py', 'r', 'utf-8') as f:
    text = f.read()

# 1. Commission update
text = text.replace('COMMISSION = 0.0004', 'COMMISSION = 0.0002')

# 2. Signature and Allocation check
old_sig = '''def open_position(symbol, allocation=2000.0, tp_pct=5.0, sl_pct=3.0, trailing=True, source="MANUAL", owner=None,
                  tp_price=None, sl_price=None):
    """Yeni pozisyon acar (owner'a ozel). tp_price/sl_price verilirse fiyat bazli emir kullanilir.
    (success, message) dondurur."""
    clean = symbol.replace(".IS", "").replace(".is", "").upper().strip()
    if not clean:
        return False, "Sembol gerekli"

    try:
        allocation = float(allocation)
    except (TypeError, ValueError):
        return False, "Gecersiz tutar"
    if allocation < 100:
        return False, "Minimum islem tutari 100 TL"'''

new_sig = '''def open_position(symbol, allocation=2000.0, tp_pct=5.0, sl_pct=3.0, trailing=True, source="MANUAL", owner=None,
                  tp_price=None, sl_price=None, price=None, qty=None):
    """Yeni pozisyon acar (owner'a ozel). tp_price/sl_price verilirse fiyat bazli emir kullanilir.
    (success, message) dondurur."""
    clean = symbol.replace(".IS", "").replace(".is", "").upper().strip()
    if not clean:
        return False, "Sembol gerekli"

    if allocation is not None:
        try:
            allocation = float(allocation)
        except (TypeError, ValueError):
            return False, "Gecersiz tutar"'''

text = text.replace(old_sig, new_sig)


# 3. Price and Shares Logic
old_logic = '''    price, src = _get_live_price(clean)
    if not price or price <= 0:
        return False, f"{clean} icin guncel fiyat alinamadi"

    if tp_price is not None and tp_price <= price:
        return False, f"K?r Al fiyati anlik fiyattan yuksek olmali ({price:.2f} TL uzeri)"
    if sl_price is not None and sl_price >= price:
        return False, f"Zarar Kes fiyati anlik fiyattan dusuk olmali ({price:.2f} TL alti)"

    cash = _get_cash(owner)
    if allocation > cash:
        return False, f"Yetersiz bakiye (Kullanilabilir: {cash:.2f} TL)"

    entry_price = round(price * 1.0015, 2)  # slipaj
    shares = int(allocation // entry_price)
    if shares <= 0:
        return False, "Bu fiyattan lot alinamadi (tutar cok dusuk)"

    cost = shares * entry_price * (1 + COMMISSION)
    if cost > cash:
        shares = int(cash // (entry_price * (1 + COMMISSION)))
        if shares <= 0:
            return False, "Yetersiz bakiye"
        cost = shares * entry_price * (1 + COMMISSION)'''

new_logic = '''    live_price, src = _get_live_price(clean)
    if not live_price or live_price <= 0:
        return False, f"{clean} icin guncel fiyat alinamadi"

    manual_price = _f(price)
    if manual_price is not None:
        entry_price = round(manual_price, 2)
        base_price = entry_price
    else:
        entry_price = round(live_price * 1.0015, 2)  # slipaj
        base_price = live_price

    if tp_price is not None and tp_price <= base_price:
        return False, f"Kâr Al fiyati alis fiyattan yuksek olmali ({base_price:.2f} TL uzeri)"
    if sl_price is not None and sl_price >= base_price:
        return False, f"Zarar Kes fiyati alis fiyattan dusuk olmali ({base_price:.2f} TL alti)"

    manual_qty = _f(qty)
    if manual_qty is not None and manual_qty > 0:
        shares = int(manual_qty)
    elif allocation is not None and allocation > 0:
        shares = int(allocation // entry_price)
    else:
        return False, "Tutar veya adet belirtilmeli"

    if shares <= 0:
        return False, "Bu fiyattan lot alinamadi (tutar cok dusuk)"

    cost = shares * entry_price * (1 + COMMISSION)
    
    cash = _get_cash(owner)
    if cost > cash:
        shares = int(cash // (entry_price * (1 + COMMISSION)))
        if shares <= 0:
            return False, f"Yetersiz bakiye (Kullanilabilir: {cash:.2f} TL)"
        cost = shares * entry_price * (1 + COMMISSION)'''

text = text.replace(old_logic, new_logic)


# Ayrica sql inserts kismindaki price -> live_price yapilmali
text = text.replace('entry_price, source, price, now))', 'entry_price, source, live_price, now))')


with codecs.open('services/live_trade_monitor.py', 'w', 'utf-8') as f:
    f.write(text)

print("PATCH APPLIED")
