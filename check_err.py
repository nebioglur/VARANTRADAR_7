# -*- coding: utf-8 -*-
with open('server.py', 'r', encoding='utf-8') as f:
    content = f.read()
import re
new_ping = r'''@app.route('/api/ping')
def api_ping():
    return jsonify({"bg_error": BACKGROUND_ERROR})
'''
if "api_ping" not in content:
    content = content.replace("def api_logs():", new_ping + "\n@app.route('/api/logs')\ndef api_logs():")
with open('server.py', 'w', encoding='utf-8') as f:
    f.write(content)
