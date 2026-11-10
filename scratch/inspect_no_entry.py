import json

with open('scratch/verd_breakout.json', encoding='utf-8') as f:
    d = json.load(f)

items = [x for x in d.get('data', []) if x.get('entry_status') == 'NO_ENTRY']
print("Total NO_ENTRY count:", len(items))
first = items[0]
for k, v in first.items():
    print(f"{k}: {repr(v)}")
