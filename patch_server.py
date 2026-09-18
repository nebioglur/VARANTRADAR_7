with open("server.py", "r", encoding="utf-8") as f:
    text = f.read()

import re

old_block = r"def api_simulation_terminal_close\(\):.*?return jsonify\(\{.*?\}\), 500"
new_block = """def api_simulation_terminal_close():
    \"\"\"Manuel anlik satis (acik pozisyonu kapat).\"\"\"
    try:
        from services.live_trade_monitor import close_position
        data = request.get_json(force=True, silent=True) or {}
        pos_id = data.get('id')
        if not pos_id:
            return jsonify({"status": "error", "message": "Pozisyon id gerekli"}), 400
        ok, msg = close_position(int(pos_id), reason="MANUEL KAPATMA (Kullanici)", owner=get_owner_key())
        return jsonify({"status": "success" if ok else "error", "message": msg}), (200 if ok else 400)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/simulation/terminal/close_by_symbol', methods=['POST'])
def api_simulation_terminal_close_by_symbol():
    \"\"\"Sembole gore acik pozisyonlari kapat.\"\"\"
    try:
        from services.live_trade_monitor import close_position_by_symbol
        data = request.get_json(force=True, silent=True) or {}
        symbol = data.get('symbol')
        if not symbol:
            return jsonify({"status": "error", "message": "Sembol gerekli"}), 400
        ok, msg = close_position_by_symbol(symbol, reason="MANUEL KAPATMA (Portfoyden SAT)", owner=get_owner_key())
        return jsonify({"status": "success" if ok else "error", "message": msg}), (200 if ok else 400)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500"""

text = re.sub(old_block, new_block, text, flags=re.DOTALL)

with open("server.py", "w", encoding="utf-8") as f:
    f.write(text)

print("SERVER PATCH DONE")
