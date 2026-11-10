with open('ui/app.js', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find('function loadV8Breakout')
if idx != -1:
    print(text[idx:idx+2500])
