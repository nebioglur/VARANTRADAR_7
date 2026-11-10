with open('server.py', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

idx = text.find('def auto_send_v8_signals():')
end_idx = text.find('def ', idx+50)
print(text[idx:end_idx])
