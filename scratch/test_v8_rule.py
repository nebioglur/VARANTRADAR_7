import json

with open('dashboard_cache.json', 'r', encoding='utf-8') as f:
    dash = json.load(f)

all_stats = dash.get("all_symbols_stats", {})

def _stats_rel_vol(data):
    v = data.get("Volume", 0)
    av = data.get("Avg_Volume_10d", 0) or 0
    return round(v / av, 2) if av > 0 else 1.0

def _v8_live_price(data):
    return float(data.get("Price") or data.get("Daily_Close") or 0.0)

breakout_list = []
for sym, data in all_stats.items():
    if data.get("Price_Stale") and not data.get("v8_breakout", {}).get("is_breakout"):
        continue
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
        breakout_list.append(row)
        continue

    disc = data.get("v8_discovery") or {}
    state = disc.get("state")
    if state in ("READY", "PREPARING", "WATCH"):
        rel_vol = _stats_rel_vol(data)
        breakout_list.append({
            "symbol": sym,
            "price": _v8_live_price(data),
            "change_pct": data.get("Change_Pct", 0.0),
            "volume": data.get("Volume", 0),
            "is_breakout": False,
            "status": "DISCOVERY_" + state,
            "breakout_score": disc.get("preparation_score", 0.0),
            "fakeout_risk": 0.0,
            "volume_strength": rel_vol,
            "entry_status": "WAIT",
            "entry_reasons": disc.get("reasons") or ["Kırılım bekleniyor; hazırlık sinyali mevcut."],
            "momentum_speed": "PREPARING",
        })
    elif data.get("Daily_Close") or data.get("Price"):
        price = _v8_live_price(data)
        change = float(data.get("Change_Pct") or 0)
        rel_vol = _stats_rel_vol(data)
        fallback_score = max(35.0, min(65.0, 48.0 + change * 2.0 + (rel_vol - 1.0) * 5.0))
        breakout_list.append({
            "symbol": sym,
            "price": price,
            "change_pct": change,
            "volume": data.get("Volume", 0),
            "is_breakout": False,
            "status": "DISCOVERY_WATCH",
            "breakout_score": round(fallback_score, 1),
            "fakeout_risk": 0.0,
            "volume_strength": rel_vol,
            "entry_status": "WAIT",
            "entry_reasons": ["Günlük tarama adayı; V8 kırılım teyidi bekleniyor."],
            "momentum_speed": "NORMAL",
        })

breakout_list = sorted(
    breakout_list,
    key=lambda x: (
        x.get("entry_status") == "ENTER",
        x.get("breakout_score", 0) - x.get("fakeout_risk", 0),
    ),
    reverse=True,
)[:80]

for row in breakout_list:
    try:
        chg = float(row.get("change_pct") or row.get("intraday_change_pct") or 0)
    except (TypeError, ValueError):
        chg = 0.0
    if chg >= 5.0:
        row["entry_status"] = "NO_ENTRY"
        row["ceiling_risk"] = True
        row["entry_reasons"] = [
            f"[TAVAN RİSKİ] +{chg:.1f} ile kovalama bölgesinde; tavan sonrası teyit beklenmeli"
        ] + list(row.get("entry_reasons") or [])

from collections import Counter
counts = Counter(r.get("entry_status") for r in breakout_list)
print("Result counts:", counts)
waits = [r.get("symbol") for r in breakout_list if r.get("entry_status") == "WAIT"]
print("Wait symbols:", waits)
