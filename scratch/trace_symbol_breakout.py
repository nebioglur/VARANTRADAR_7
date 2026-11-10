import sys, os
sys.path.insert(0, os.path.abspath('.'))

import server
import json
from v8_engine.execution import ExecutionEngine

with open('dashboard_cache.json', 'r', encoding='utf-8') as f:
    stats = json.load(f).get("all_symbols_stats", {})

exec_engine = ExecutionEngine()

for sym in ["ADGYO.IS", "GARAN.IS"]:
    data = stats.get(sym, {})
    bo = data.get("v8_breakout")
    eval_res = exec_engine.evaluate_entry(bo, "BULL")
    row = dict(bo)
    row["symbol"] = sym
    row["price"] = server._v8_live_price(data)
    row["change_pct"] = data.get("Change_Pct", 0.0)
    row["volume"] = data.get("Volume", 0)
    row["volume_strength"] = server._stats_rel_vol(data)
    row["entry_status"] = eval_res.get("entry_status")
    row["entry_reasons"] = eval_res.get("reasons")
    
    print(f"\n--- {sym} before gate ---")
    print("entry_status:", row["entry_status"])
    print("change_pct:", row["change_pct"])
    print("Price_Stale:", data.get("Price_Stale"))
    
    gated = server._v8_gate_enter_row(row, sym, data)
    print(f"--- {sym} after gate ---")
    print("entry_status:", gated["entry_status"])
    print("entry_reasons:", gated["entry_reasons"])
