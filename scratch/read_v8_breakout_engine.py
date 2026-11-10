with open('v8_engine/breakout.py', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find('def analyze_breakout')
if idx != -1:
    print(text[idx:idx+3000])
