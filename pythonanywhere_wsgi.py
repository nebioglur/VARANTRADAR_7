"""
PythonAnywhere WSGI Configuration for VarantRadar Pro
Bu dosyanın içeriğini PythonAnywhere Web sekmesindeki WSGI configuration file içine kopyalayabilirsiniz.
"""
import sys
import os

# 1. Proje yolunu dinamik olarak sys.path'e ekle
username = os.environ.get("USER", "nebioglur")
project_home = f"/home/{username}/VARANTRADAR_7"

if not os.path.exists(project_home):
    # Eğer kullanıcı adı farklıysa otomatik tespit et
    base_home = os.path.expanduser("~")
    project_home = os.path.join(base_home, "VARANTRADAR_7")

if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Çalışma dizinini proje kökü yap
os.chdir(project_home)

# 2. Ortam değişkenlerini ayarla
os.environ["ENABLE_BACKGROUND_SERVICES"] = "true"
os.environ["ENVIRONMENT"] = "production"

# 3. Flask uygulamasını 'application' olarak dışa aktar
from server import app as application
