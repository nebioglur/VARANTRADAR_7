"""
PythonAnywhere WSGI Configuration for VarantRadar Pro
Bu dosyanın içeriğini PythonAnywhere Web sekmesindeki WSGI configuration file içine kopyalayabilirsiniz.
"""
import sys
import os

# 0. PythonAnywhere Free Tier Proxy (Giden baglantilar icin zorunlu)
os.environ["http_proxy"] = "http://proxy.server:3128"
os.environ["https_proxy"] = "http://proxy.server:3128"
os.environ["HTTP_PROXY"] = "http://proxy.server:3128"
os.environ["HTTPS_PROXY"] = "http://proxy.server:3128"

# 1. Proje yolunu dinamik olarak sys.path'e ekle
username = os.environ.get("USER", "varantradarpro")
project_home = f"/home/{username}/VARANTRADAR_7"

if not os.path.exists(project_home):
    base_home = os.path.expanduser("~")
    project_home = os.path.join(base_home, "VARANTRADAR_7")

if project_home not in sys.path:
    sys.path.insert(0, project_home)

os.chdir(project_home)

# 2. Ortam değişkenlerini ayarla
# PythonAnywhere web workers do not support long-lived background threads.
# The separate pythonanywhere_worker.py Always-on task owns those services.
os.environ["ENABLE_BACKGROUND_SERVICES"] = "true"
os.environ["ENVIRONMENT"] = "production"
os.environ["SECRET_KEY"] = "varantradar_secret_key_2026_prod_secure"
os.environ["TELEGRAM_PRIMARY_HOST"] = "pythonanywhere"
os.environ["IS_PRIMARY_TELEGRAM"] = "true"

# 3. Flask uygulamasını 'application' olarak dışa aktar
from server import app as application
