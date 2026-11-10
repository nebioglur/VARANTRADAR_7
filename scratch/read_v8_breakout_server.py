with open('server.py', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find("'/api/v8/radar/breakout'")
if idx == -1:
    idx = text.find('"/api/v8/radar/breakout"')
print("Breakout route at:", idx)
if idx != -1:
    print(text[idx:idx+2500])
