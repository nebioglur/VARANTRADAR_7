import urllib.request, json

url = 'https://varantradarpro.pythonanywhere.com/api/system/git_pull?token=deploy_now'
req = urllib.request.Request(url)
req.add_header('User-Agent', 'Mozilla/5.0')

try:
    with urllib.request.urlopen(req, timeout=30) as resp:
        res = json.loads(resp.read().decode('utf-8'))
        print("DEPLOY RESULT:", json.dumps(res, indent=2, ensure_ascii=False))
except Exception as e:
    print("DEPLOY ERROR:", e)
