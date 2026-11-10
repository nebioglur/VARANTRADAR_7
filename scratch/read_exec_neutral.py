with open('v8_engine/execution.py', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find('if market_regime == "NEUTRAL":')
print("NEUTRAL check at:", idx)
if idx != -1:
    print(text[idx-50:idx+400])
