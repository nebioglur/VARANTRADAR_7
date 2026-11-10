import json

with open('scratch/verd_breakout.json', encoding='utf-8') as f:
    verd = json.load(f)

with open('dashboard_cache.json', encoding='utf-8') as f:
    dash = json.load(f)

v_data = verd.get('data', [])
dash_stats = dash.get('all_symbols_stats', {})

print("Verdent first 10:")
for x in v_data[:10]:
    print(x['symbol'], x['breakout_score'], x['entry_status'], x.get('status'))

# Why was ACSEL not included?
# Let's check if Verdent's endpoint filtered by volume or something else:
acsel_vol = dash_stats.get('ACSEL.IS', {}).get('Volume', 0)
fzlgy_vol = dash_stats.get('FZLGY.IS', {}).get('Volume', 0)
print(f"ACSEL Volume: {acsel_vol}, FZLGY Volume: {fzlgy_vol}")

# Let's check min volume in Verdent
v_vols = [x.get('volume', 0) for x in v_data]
print(f"Min volume in Verdent: {min(v_vols)}, Max: {max(v_vols)}")
for x in v_data:
    if x.get('volume', 0) < 5000000:
        print(f"Low vol symbol in Verdent: {x['symbol']} vol={x.get('volume')}")
