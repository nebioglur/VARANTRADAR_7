with open('server.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('return jsonify({"status": "success", "stats": stats})', 'return jsonify({"status": "success", "stats": sanitize_for_json(stats)})')

with open('server.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("Fixed api_winrate_stats")
