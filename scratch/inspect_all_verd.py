import json

with open('scratch/verd_breakout.json', encoding='utf-8') as f:
    d = json.load(f)

print(f"Total items: {len(d.get('data', []))}")
for i, item in enumerate(d.get('data', [])):
    status = item.get('entry_status')
    sym = item.get('symbol')
    score = item.get('breakout_score')
    reasons = item.get('entry_reasons', [])
    first_r = reasons[0] if reasons else ''
    safe_r = first_r.encode('ascii', 'replace').decode('ascii')
    print(f"{i+1:2d}. {sym:10s} | {status:10s} | {score} | {safe_r[:50]}")
