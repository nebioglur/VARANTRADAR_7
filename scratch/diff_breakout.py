import json

with open('dashboard_cache.json', 'r', encoding='utf-8') as f:
    dash = json.load(f)

with open('scratch/verd_breakout.json', 'r', encoding='utf-8') as f:
    verd = json.load(f)

# Let's see what Verdent's breakout list contains vs our breakout_list logic
v_data = verd.get('data', [])
print("Verdent items:", len(v_data))
print("Verdent WAIT items:", [x['symbol'] for x in v_data if x['entry_status'] == 'WAIT'])
print("Verdent NO_ENTRY items count:", len([x for x in v_data if x['entry_status'] == 'NO_ENTRY']))

# Now let's check in server.py what the actual api_v8_radar_breakout() does
# Let's inspect how Verdent generated its breakout response!
