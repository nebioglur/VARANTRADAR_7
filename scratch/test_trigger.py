import urllib.request
import urllib.error

url = 'https://varantradarpro.pythonanywhere.com/api/system/git_pull?token=deploy_now'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
try:
    res = urllib.request.urlopen(req, timeout=30)
    print("STATUS:", res.status)
    print("RESPONSE:", res.read().decode('utf-8'))
except urllib.error.HTTPError as e:
    print("HTTP ERROR:", e.code)
    print("BODY:", e.read().decode('utf-8', errors='ignore'))
except Exception as ex:
    print("EXCEPTION:", ex)
