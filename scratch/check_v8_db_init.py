with open('v8_engine/database.py', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

print('v8_tg_sent in v8_engine/database.py:', 'v8_tg_sent' in text)
idx = text.find('init_db')
print(text[idx:idx+800])
