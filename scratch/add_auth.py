import sys

with open('server.py', 'r', encoding='utf-8') as f:
    content = f.read()

auth_code = """
# ============ BASIC AUTH (GÜVENLİK) ============
import os
from flask import request, Response

# Çevre değişkenlerinden (Render) al, yoksa varsayılanları kullan
ADMIN_USER = os.environ.get('ADMIN_USER', 'admin')
ADMIN_PASS = os.environ.get('ADMIN_PASS', 'radar123')

def check_auth(username, password):
    return username == ADMIN_USER and password == ADMIN_PASS

def authenticate():
    return Response(
        'VarantRadar Pro - Yetkisiz Erisim. Lutfen kullanici adi ve sifre giriniz.', 401,
        {'WWW-Authenticate': 'Basic realm="VarantRadar Pro Login"'}
    )

@app.before_request
def require_auth_for_all():
    # CORS oncesi preflight isteklerine izin ver
    if request.method == 'OPTIONS':
        return
        
    auth = request.authorization
    if not auth or not check_auth(auth.username, auth.password):
        return authenticate()
# ===============================================

"""

# Insert right after `app = Flask(__name__)` or `CORS(app)`
if 'CORS(app)' in content:
    content = content.replace('CORS(app)', 'CORS(app)\n' + auth_code)
else:
    content = content.replace('app = Flask(__name__)', 'app = Flask(__name__)\n' + auth_code)

with open('server.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Auth code injected")
