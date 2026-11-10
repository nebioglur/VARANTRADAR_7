import sys, os
sys.path.insert(0, os.path.abspath('.'))

import server
import json
from v8_engine.execution import ExecutionEngine

with open('dashboard_cache.json', 'r', encoding='utf-8') as f:
    stats = json.load(f).get("all_symbols_stats", {})

exec_engine = ExecutionEngine()

for sym in ["ADGYO.IS", "GARAN.IS", "KONTR.IS"]:
    data = stats.get(sym, {})
    bo = data.get("v8_breakout")
    print(f"\n=== {sym} ===")
    print("v8_breakout:", bo)
    eval_res = exec_engine.evaluate_entry(bo, "BULL")
    print("evaluate_entry under BULL:", eval_res)
    row = dict(bo)
    row["entry_status"] = eval_res.get("entry_status")
    row["entry_reasons"] = eval_res.get("reasons")
    gate_res = server._v8_gate_enter_row(row, sym, data)
    print("gate_enter_row under BULL:", gate_res.get("entry_status"), gate_res.get("entry_reasons"))
