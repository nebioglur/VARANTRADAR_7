import json

with open('scratch/verd_breakout.json', 'r', encoding='utf-8') as f:
    verd_bo = json.load(f)

with open('v8_breakout_cache.json', 'w', encoding='utf-8') as f:
    json.dump(verd_bo, f, ensure_ascii=False, indent=2)

print("v8_breakout_cache.json written. Items:", len(verd_bo.get('data', [])))
