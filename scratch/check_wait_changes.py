import json

with open('scratch/verd_breakout.json', encoding='utf-8') as f:
    verd = json.load(f)

for item in verd.get('data', []):
    if item.get('entry_status') == 'WAIT':
        print(f"{item.get('symbol'):8s}: change_pct = {item.get('change_pct')}")
