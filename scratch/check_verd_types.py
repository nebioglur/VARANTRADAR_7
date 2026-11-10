import json

with open('scratch/verd_breakout.json', encoding='utf-8') as f:
    verd = json.load(f)

data = verd.get('data', [])

print(f"Total data items: {len(data)}")
for i, item in enumerate(data):
    stat = item.get('status')
    e_stat = item.get('entry_status')
    is_bo = item.get('is_breakout')
    score = item.get('breakout_score')
    sym = item.get('symbol')
    print(f"{i+1:2d}. {sym:8s} | is_bo: {is_bo} | status: {stat:20s} | entry: {e_stat:10s} | score: {score}")
