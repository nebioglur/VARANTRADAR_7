import os

with open('server.py', 'r', encoding='utf-8') as f:
    text = f.read()

target = '@app.route("/api/health")'
idx = text.find(target)
if idx != -1:
    insert = """
@app.route("/api/v8/market/regime", methods=["GET"])
@login_required
def api_v8_market_regime():
    regime_data = GLOBAL_DASHBOARD_CACHE.get("v8_market_regime", {"regime": "UNKNOWN", "score": 0})
    return jsonify(regime_data)
"""
    if 'api_v8_market_regime' not in text:
        text = text[:idx] + insert + "\n" + text[idx:]
        with open('server.py', 'w', encoding='utf-8') as f:
            f.write(text)
        print('Endpoint added.')
    else:
        print('Already exists')
else:
    print('Target not found')
