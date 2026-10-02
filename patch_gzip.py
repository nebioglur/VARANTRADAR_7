import os
import re

def patch_server():
    try:
        with open("server.py", "r", encoding="utf-8") as f:
            content = f.read()
            
        gzip_code = """
import gzip
import io
from flask import request

@app.after_request
def compress_response(response):
    accept_encoding = request.headers.get('Accept-Encoding', '')
    if 'gzip' not in accept_encoding.lower():
        return response
    if response.status_code < 200 or response.status_code >= 300:
        return response
    if 'Content-Encoding' in response.headers:
        return response
    if response.content_length is not None and response.content_length < 500:
        return response
        
    gzip_buffer = io.BytesIO()
    with gzip.GzipFile(mode='wb', fileobj=gzip_buffer) as gzip_file:
        gzip_file.write(response.get_data())
    
    response.set_data(gzip_buffer.getvalue())
    response.headers['Content-Encoding'] = 'gzip'
    response.headers['Content-Length'] = len(response.get_data())
    return response
"""
        if "compress_response" not in content:
            # Find app = Flask(...)
            app_pattern = r"(app\s*=\s*Flask\([^\)]+\))"
            if re.search(app_pattern, content):
                content = re.sub(app_pattern, r"\1\n" + gzip_code, content, count=1)
                with open("server.py", "w", encoding="utf-8") as f:
                    f.write(content)
                print("server.py: GZIP sıkıştırma başarıyla eklendi.")
            else:
                print("app = Flask() bulunamadı.")
        else:
            print("server.py: GZIP zaten ekli.")
            
    except Exception as e:
        print(f"server.py Hata: {e}")

def patch_app_js():
    try:
        with open("ui/app.js", "r", encoding="utf-8") as f:
            content = f.read()
            
        # setInterval(fetchDashboardData, 5000); -> setInterval(fetchDashboardData, 60000);
        new_content = re.sub(r"setInterval\(\s*fetchDashboardData\s*,\s*5000\s*\)", "setInterval(fetchDashboardData, 60000)", content)
        
        if content != new_content:
            with open("ui/app.js", "w", encoding="utf-8") as f:
                f.write(new_content)
            print("ui/app.js: Yenileme süresi 60 saniyeye çıkarıldı.")
        else:
            print("ui/app.js: Zaten güncel veya bulunamadı.")
            
    except Exception as e:
        print(f"ui/app.js Hata: {e}")

if __name__ == "__main__":
    patch_server()
    patch_app_js()
