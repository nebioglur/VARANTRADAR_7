import sys, os
sys.path.insert(0, os.path.abspath('.'))

import server
import json

with open('dashboard_cache.json', 'r', encoding='utf-8') as f:
    stats = json.load(f).get("all_symbols_stats", {})

for sym in ["ADGYO.IS", "GARAN.IS", "KONTR.IS"]:
    data = stats.get(sym, {})
    bo = data.get("v8_breakout")
    print(f"\n=== {sym} ===")
    print("v8_breakout:", bo)
    eval_res = server._DynExecEngine().evaluate_entry(bo, "BULL")
    print("evaluate_entry under BULL:", eval_res)
    gate_res = server._v8_gate_enter_row(dict(bo), sym, data)
    print("gate_enter_row under BULL:", gate_res.get("entry_status"), gate_res.get("entry_reasons"))
