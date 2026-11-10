with open('v8_engine/breakout.py', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find('if market_regime in ["BEAR", "STRONG_BEAR"]:')
if idx != -1:
    print(text[idx:idx+1500])
