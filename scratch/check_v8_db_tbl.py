with open('server.py', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

idx = text.find('def auto_send_v8_signals():')
end_idx = text.find('def ', idx+50)
v8_func = text[idx:end_idx]

# Check dependencies inside auto_send_v8_signals
print('_V8_TG_SENT in file:', '_V8_TG_SENT' in text)
print('v8_tg_sent in text:', 'v8_tg_sent' in text)
