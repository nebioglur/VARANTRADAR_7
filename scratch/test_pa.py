import urllib.request
import urllib.error

req = urllib.request.Request('https://varantradar.pythonanywhere.com/', headers={'User-Agent': 'Mozilla/5.0'})
try:
    res = urllib.request.urlopen(req, timeout=10)
    print("STATUS:", res.status)
    print(res.read().decode('utf-8', errors='ignore'))
except urllib.error.HTTPError as e:
    print("HTTP ERROR CODE:", e.code)
    body = e.read().decode('utf-8', errors='ignore')
    print(body)
except Exception as ex:
    print("EXCEPTION:", ex)
