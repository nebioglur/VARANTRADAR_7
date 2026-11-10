with open('v8_engine/regime.py', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find('def _fetch_index_df(self):')
print("Index fetch at:", idx)
if idx != -1:
    print(text[idx:idx+1200])
