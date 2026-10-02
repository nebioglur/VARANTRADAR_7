import re

with open('server.py', 'r', encoding='utf-8') as f:
    c = f.read()

# Replace the entire api_simulation_daily_pnl function
import re

old_func_pattern = r"@app\.route\('/api/simulation/daily_pnl', methods=\['GET'\]\)\ndef api_simulation_daily_pnl\(\):.*?@app\.route\('/api/simulation/send_telegram', methods=\['POST'\]\)"

new_func = """@app.route('/api/simulation/daily_pnl', methods=['GET'])
def api_simulation_daily_pnl():
    try:
        from services.backtester import AdvancedBacktester
        backtester = AdvancedBacktester()
        res = backtester.run_simulation()
        if res.get("status") == "error":
            return jsonify(res), 500
        return jsonify(res)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/simulation/send_telegram', methods=['POST'])"""

c = re.sub(old_func_pattern, new_func, c, flags=re.DOTALL)

with open('server.py', 'w', encoding='utf-8') as f:
    f.write(c)

print("SUCCESS")
