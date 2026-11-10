import json

with open('scratch/verd_breakout.json', encoding='utf-8') as f:
    verd = json.load(f)

for item in verd.get('data', []):
    if item.get('entry_status') == 'NO_ENTRY' and not item.get('is_breakout'):
        r = item.get('entry_reasons', [])
        print(f"{item.get('symbol'):8s}: {r}")
