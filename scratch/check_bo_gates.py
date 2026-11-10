with open('server.py', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

idx = text.find('def api_v8_radar_breakout():')
end_idx = text.find('def api_v8_radar_discovery():', idx)

sub = text[idx:end_idx]
for sym in ['_apply_v8_final_gate', '_v8_gate_enter_row', 'auto_send_v8']:
    print(sym, 'count in breakout endpoint:', sub.count(sym))
