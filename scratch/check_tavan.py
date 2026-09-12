with open('server.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    if 'def api_winrate_stats' in line or 'def api_tavan_tracker' in line or 'def api_tavan_history' in line:
        print(f"--- {line.strip()} ---")
        for j in range(i, min(i+10, len(lines))):
            if 'return jsonify' in lines[j]:
                print(lines[j].strip())
