import re

with open('server.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Remove the Basic Auth block
basic_auth_regex = r"# ============ BASIC AUTH \(GÜVENLİK\) ============.*?# ==============================================="
content = re.sub(basic_auth_regex, '', content, flags=re.DOTALL)

# Add Session Auth block
session_auth_code = """
# ============ SESSION AUTH (GÜVENLİK) ============
import os
from flask import request, Response, session, redirect, jsonify, render_template_string

app.secret_key = os.environ.get('SECRET_KEY', 'varant_pro_ultra_secret_2026_xyz')
ADMIN_USER = os.environ.get('ADMIN_USER', 'admin')
ADMIN_PASS = os.environ.get('ADMIN_PASS', 'radar123')

@app.before_request
def require_auth():
    if request.method == 'OPTIONS': return
    
    allowed = ['/login', '/logout']
    if request.path in allowed: return
    
    # Allow static assets for login page
    if request.path.endswith('.css') or request.path.endswith('.js') or request.path.endswith('.png') or request.path.endswith('.woff2'):
        return

    if not session.get('logged_in'):
        if request.path.startswith('/api/'):
            return jsonify({"status": "error", "message": "Unauthorized"}), 401
        return redirect('/login')

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        if request.form.get('username') == ADMIN_USER and request.form.get('password') == ADMIN_PASS:
            session['logged_in'] = True
            return redirect('/')
        else:
            error = "Hatalı kullanıcı adı veya şifre!"
            
    # Send login.html but inject error if any
    try:
        with open('ui/login.html', 'r', encoding='utf-8') as f:
            html = f.read()
            if error:
                html = html.replace('<!-- ERROR_PLACEHOLDER -->', f'<div class="error-msg">{error}</div>')
            return html
    except:
        return "login.html bulunamadi", 404

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect('/login')
# =================================================
"""

if 'CORS(app)' in content:
    content = content.replace('CORS(app)', 'CORS(app)\n' + session_auth_code)
else:
    content = content.replace('app = Flask(__name__)', 'app = Flask(__name__)\n' + session_auth_code)

with open('server.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("Session auth added")
