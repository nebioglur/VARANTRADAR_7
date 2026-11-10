with open('server.py', 'r', encoding='utf-8', errors='ignore') as s:
    text = s.read()

target = 'breakout_list})'
idx = text.find(target)
print('Target index:', idx)
print(text[max(0, idx-400):min(len(text), idx+100)])
