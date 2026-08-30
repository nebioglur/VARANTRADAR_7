with open('server.py', 'r', encoding='utf-8') as f:
    for i, line in enumerate(f):
        if 'return jsonify' in line and 'sanitize_for_json' not in line and '"error"' not in line:
            print(f"{i}: {line.strip()}")
