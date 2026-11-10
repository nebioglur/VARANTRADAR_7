import json

with open('dashboard_cache.json', 'r', encoding='utf-8') as f:
    cache = json.load(f)

stats = cache.get('all_symbols_stats', {})

enter_symbols = []
for sym, data in stats.items():
    ex = data.get('v8_execution') or {}
    bo = data.get('v8_breakout') or {}
    if bo.get('is_breakout') and ex.get('entry_status') == 'ENTER':
        enter_symbols.append((sym, data))

print(f"Total symbols with breakout + execution ENTER: {len(enter_symbols)}")

import sys, os
sys.path.insert(0, os.getcwd())

from server import (
    _v8_regime_locked,
    _v8_defense_mode_check,
    _v8_a_class_gate,
    _v8_entry_confirmation,
    _v8_gate_enter_row,
    GLOBAL_DASHBOARD_CACHE
)

GLOBAL_DASHBOARD_CACHE['all_symbols_stats'] = stats
GLOBAL_DASHBOARD_CACHE['v8_market_regime'] = cache.get('v8_market_regime', {})

print(f"Regime locked: {_v8_regime_locked()} (regime: {(cache.get('v8_market_regime') or {}).get('regime')})")

for sym, data in enter_symbols:
    bo = dict(data.get('v8_breakout'))
    bo['symbol'] = sym
    bo['entry_status'] = 'ENTER'
    bo['entry_reasons'] = data.get('v8_execution', {}).get('reasons', [])
    
    # Check regime
    if _v8_regime_locked():
        def_ok = _v8_defense_mode_check(bo, sym, data)
        print(f"[{sym}] Regime locked. Defense mode: {def_ok}")
        continue
        
    # Check a class
    a_ok, a_reasons = _v8_a_class_gate(bo, sym, data)
    if not a_ok:
        print(f"[{sym}] A-class REJECTED: {a_reasons}")
        continue
        
    # Check confirmation
    price = data.get('Price') or bo.get('price') or 0
    cstate, cmsg = _v8_entry_confirmation(sym, price)
    print(f"[{sym}] A-class OK! Confirmation: {cstate} - {cmsg}")
