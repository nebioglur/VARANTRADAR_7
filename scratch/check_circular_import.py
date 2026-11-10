with open('main.py', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

target = 'from server import GLOBAL_DASHBOARD_CACHE'
idx = text.find(target)
print('Target index:', idx)
print(text[max(0, idx-100):min(len(text), idx+300)])
