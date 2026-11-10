with open('main.py', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

target = 'def run_simulation_api('
idx = text.find(target)
print('Target index:', idx)
print(text[idx:idx+1500])
