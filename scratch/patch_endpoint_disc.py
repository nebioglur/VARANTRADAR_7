import os

with open('server.py', 'r', encoding='utf-8') as f:
    text = f.read()

target = "@app.route('/api/v8/market/regime', methods=['GET'])"
idx = text.find(target)
if idx != -1:
    insert = """
@app.route('/api/v8/radar/discovery', methods=['GET'])
@login_required
def api_v8_radar_discovery():
    all_stats = GLOBAL_DASHBOARD_CACHE.get("all_symbols_stats", {})
    discovery_list = []
    
    for sym, data in all_stats.items():
        disc = data.get("v8_discovery")
        if disc and disc.get("state") in ["READY", "PREPARING", "WATCH"]:
            # Combine some essential pricing data
            disc["price"] = data.get("Daily_Close", 0.0)
            disc["change_pct"] = data.get("Change_Pct", 0.0)
            disc["volume"] = data.get("Volume", 0)
            discovery_list.append(disc)
            
    # Puanlara gore sirala
    discovery_list = sorted(discovery_list, key=lambda x: x.get("preparation_score", 0), reverse=True)
    return jsonify({"status": "success", "data": discovery_list})
"""
    if 'api_v8_radar_discovery' not in text:
        text = text[:idx] + insert + "\n" + text[idx:]
        with open('server.py', 'w', encoding='utf-8') as f:
            f.write(text)
        print('Discovery Endpoint added.')
    else:
        print('Already exists')
else:
    print('Target not found')
