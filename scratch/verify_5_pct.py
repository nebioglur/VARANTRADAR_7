import json

with open('scratch/verd_breakout.json', encoding='utf-8') as f:
    verd = json.load(f)

v_data = verd.get('data', [])

# Check change_pct of all items in Verdent
above_5 = [x for x in v_data if float(x.get('change_pct', 0)) >= 5.0]
below_5 = [x for x in v_data if float(x.get('change_pct', 0)) < 5.0]

print(f"Total: {len(v_data)}")
print(f"Above or equal 5.0: {len(above_5)}")
print(f"Below 5.0: {len(below_5)}")

print("Statuses of above 5.0:", set(x.get('entry_status') for x in above_5))
print("Statuses of below 5.0:", set(x.get('entry_status') for x in below_5))
