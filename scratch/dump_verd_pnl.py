import json

with open('scratch/verd_daily_pnl.json', encoding='utf-8') as f:
    verd_pnl = json.load(f)

print(json.dumps(verd_pnl, indent=2, ensure_ascii=False)[:3000])
