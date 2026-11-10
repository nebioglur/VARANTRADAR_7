import json

# Load dashboard_cache.json
with open('dashboard_cache.json', 'r', encoding='utf-8') as f:
    cache = json.load(f)

all_stats = cache.get("all_symbols_stats", {})
cache_ts = cache.get("cache_timestamp")

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
        row["scan_timestamp"] = cache_ts
        row["entry_status"] = data.get("v8_execution", {}).get("entry_status", "UNKNOWN")
        row["entry_reasons"] = data.get("v8_execution", {}).get("reasons", [])
        breakout_list.append(row)
        continue

    intra = data.get("v8_breakout_1h") or {}
    intra_bo = intra.get("breakout") or {}
    if intra_bo.get("is_breakout") and intra.get("entry_status") == "ENTER":
        row = dict(intra_bo)
        row["symbol"] = sym
        row["price"] = _v8_live_price(data)
        row["change_pct"] = data.get("Change_Pct", 0.0)
        row["volume"] = data.get("Volume", 0)
        row["volume_strength"] = _stats_rel_vol(data)
        row["scan_timestamp"] = cache_ts
        row["entry_status"] = "ENTER"
        row["entry_reasons"] = ["1 saatlik barda kırılım teyidi (gün içi sinyal)"] + list(intra.get("reasons") or [])
        row["intraday_signal"] = True
        row["momentum_speed"] = intra.get("momentum_speed", "NORMAL")
        row["timeframe_quality"] = intra.get("timeframe_quality", 0)
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
            "metrics": {"relative_volume": rel_vol, "rsi": data.get("RSI", 50.0)},
            "volume_strength": rel_vol,
            "scan_timestamp": cache_ts,
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
            "metrics": {"relative_volume": rel_vol, "rsi": data.get("RSI", 50.0)},
            "volume_strength": rel_vol,
            "scan_timestamp": cache_ts,
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
c = Counter(x.get('entry_status') for x in breakout_list)
print("Breakout counts:", c)
waits = [x.get('symbol') for x in breakout_list if x.get('entry_status') == 'WAIT']
print(f"WAIT count ({len(waits)}):", waits)
