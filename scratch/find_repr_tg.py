with open('services/telegram_bot.py', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find('def send_telegram_message')
print(repr(text[idx-50:idx+350]))
