with open('server.py', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find("def _v8_gate_enter_row")
print("_v8_gate_enter_row at:", idx)
if idx != -1:
    print(text[idx:idx+2500])
