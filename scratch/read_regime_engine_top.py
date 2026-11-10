with open('v8_engine/regime.py', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find('class MarketRegimeEngine:')
if idx == -1:
    idx = text.find('class MarketRegimeEngine')

print("MarketRegimeEngine at:", idx)
if idx != -1:
    print(text[idx:idx+1500])
