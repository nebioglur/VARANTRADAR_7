with open('server.py', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

idx = text.find('Telegram\'a V8 aday listesi otomatik yollanmaz')
print(text[max(0, idx-200):min(len(text), idx+400)])
