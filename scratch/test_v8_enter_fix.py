import json

with open('dashboard_cache.json', 'r', encoding='utf-8') as f:
    cache = json.load(f)

stats = cache.get('all_symbols_stats', {})

def _stats_rel_vol(data: dict) -> float:
    try:
        v = data.get("Vol_Multiplier") or data.get("Volume_Ratio") or data.get("Hacim_Gucu")
        if v is not None:
            return float(v)
    except (TypeError, ValueError):
        pass
    vol = float(data.get("Volume", 0) or 0)
    vol_prev = float(data.get("Prev_Volume", 0) or data.get("Volume_Prev", 0) or 0)
    if vol_prev > 0:
        return round(vol / vol_prev, 2)
    return 1.0

def _v8_live_price(data: dict) -> float:
    return float(data.get("Price") or data.get("Daily_Close") or 0.0)

def _v8_a_class_gate_fixed(row: dict, sym: str, data: dict):
    reasons = []
    try:
        chg = float(row.get("change_pct") or data.get("Change_Pct") or 0)
    except (TypeError, ValueError):
        chg = 0.0
    if chg >= 9.2:
        reasons.append(f"Hisse tavana cok yakin (+{chg:+.1f}%; tavan kilitli)")
    elif chg < -2.5:
        reasons.append(f"Hisse belirgin ekside ({chg:+.1f}%)")

    try:
        vol = float(data.get("Vol_Multiplier") or data.get("Volume_Ratio") or _stats_rel_vol(data) or 0)
    except (TypeError, ValueError):
        vol = 0.0
    if vol < 0.8:
        reasons.append(f"Hacim ortalamanin altinda ({vol:.1f}x; en az 0.8x gerekli)")

    return (len(reasons) == 0, reasons)

breakout_list = []
for sym, data in stats.items():
    bo = data.get("v8_breakout")
    if bo and bo.get("is_breakout"):
        row = dict(bo)
        row["symbol"] = sym
        row["price"] = _v8_live_price(data)
        row["change_pct"] = data.get("Change_Pct", 0.0)
        row["volume"] = data.get("Volume", 0)
        row["volume_strength"] = _stats_rel_vol(data)
        row["entry_status"] = data.get("v8_execution", {}).get("entry_status", "UNKNOWN")
        row["entry_reasons"] = data.get("v8_execution", {}).get("reasons", [])
        
        # Check A-class gate
        if row["entry_status"] == "ENTER":
            a_ok, a_reasons = _v8_a_class_gate_fixed(row, sym, data)
            if not a_ok:
                row["entry_status"] = "WAIT_CONFIRMATION"
                row["entry_reasons"] = a_reasons
        
        breakout_list.append(row)

# Tavan riski kapisi (9.2% uzeri tavan)
for row in breakout_list:
    chg = float(row.get("change_pct") or 0.0)
    if chg >= 9.2:
        row["entry_status"] = "NO_ENTRY"
        row["ceiling_risk"] = True
        row["entry_reasons"] = [f"[TAVAN RISKI] +%{chg:.1f} ile tavana kilitli"]

enter_list = [r for r in breakout_list if r.get("entry_status") == "ENTER"]
wait_list = [r for r in breakout_list if r.get("entry_status") in ("WAIT_PULLBACK", "WAIT", "WAIT_CONFIRMATION")]
avoid_list = [r for r in breakout_list if r.get("entry_status") not in ("ENTER", "WAIT_PULLBACK", "WAIT", "WAIT_CONFIRMATION")]

print(f"Giris Onayli (AL): {len(enter_list)}")
for r in enter_list:
    print(f"  * {r['symbol']}: %+2.2f%% | Skor: {r.get('breakout_score')} | Fiyat: {r.get('price')}")

print(f"\nHazirlik (BEKLE): {len(wait_list)}")
print(f"Tuzak/Uzak Dur: {len(avoid_list)}")
