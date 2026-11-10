with open('server.py', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

idx = text.find('def api_v8_radar_breakout():')
end_idx = text.find('return jsonify({"status": "success", "data": breakout_list})', idx)
print(text[end_idx-400:end_idx+80])
