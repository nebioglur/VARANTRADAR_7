import requests

s = requests.Session()
s.post("https://varantradarpro.pythonanywhere.com/login", json={"username": "nebioglur", "password": "123"})
r = s.get("https://varantradarpro.pythonanywhere.com/api/telegram/test_suite", params={"check_env": 1})
print(r.status_code, r.text[:200])
