import os

with open('server.py', 'r', encoding='utf-8') as f:
    text = f.read()

target = "@app.route('/api/v8/radar/discovery', methods=['GET'])"
idx = text.find(target)
if idx != -1:
    insert = """
@app.route('/api/v8/radar/breakout', methods=['GET'])
@login_required
def api_v8_radar_breakout():
    all_stats = GLOBAL_DASHBOARD_CACHE.get("all_symbols_stats", {})
    breakout_list = []
    
    for sym, data in all_stats.items():
        bo = data.get("v8_breakout")
        if bo and bo.get("is_breakout"):
            bo["price"] = data.get("Daily_Close", 0.0)
            bo["change_pct"] = data.get("Change_Pct", 0.0)
            bo["volume"] = data.get("Volume", 0)
            breakout_list.append(bo)
            
    # Siralama: Oncelikle kaliteli kirilimlar
    breakout_list = sorted(breakout_list, key=lambda x: x.get("breakout_score", 0) - x.get("fakeout_risk", 0), reverse=True)
    return jsonify({"status": "success", "data": breakout_list})
"""
    if 'api_v8_radar_breakout' not in text:
        text = text[:idx] + insert + "\n" + text[idx:]
        with open('server.py', 'w', encoding='utf-8') as f:
            f.write(text)
        print('Breakout Endpoint added.')
    else:
        print('Already exists')
else:
    print('Target not found')
