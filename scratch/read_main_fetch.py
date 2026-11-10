with open('main.py', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

target = 'pipeline.get_clean_data(symbol'
idx = text.find(target)
print('Target index:', idx)
print(text[idx:idx+1500])
