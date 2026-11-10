import re

with open('server.py', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

# Let's inspect auto_send_v8_signals to make sure it picks candidates that have entry_status == "ENTER"
# In breakout endpoint:
# row["entry_status"] = eval_res.get("entry_status", "UNKNOWN")
# row = _v8_gate_enter_row(row, sym, data)
# row = _apply_v8_final_gate(row)

idx = text.find('def auto_send_v8_signals():')
end_idx = text.find('def api_v8_backtest_run():', idx)
if end_idx == -1:
    end_idx = text.find('@app.route(\'/api/v8/backtest/run\'', idx)
print(text[idx:end_idx])
