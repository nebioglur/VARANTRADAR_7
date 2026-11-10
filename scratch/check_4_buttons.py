import requests

s = requests.Session()
s.post("https://varantradarpro.pythonanywhere.com/login", json={"username": "nebioglur", "password": "123"})

endpoints = [
    ("1. Test Mesajı", "/api/telegram/test"),
    ("2. Dağ Kekliği (Tavan)", "/api/telegram/send_tavan_candidates"),
    ("3. Özel Sıralama", "/api/telegram/send_special_ranking"),
    ("4. Günün Pusulası", "/api/telegram/send_morning_compass")
]

print("=== TELEGRAM BUTTONS COMPREHENSIVE VERIFICATION ===")
for name, ep in endpoints:
    r = s.post(f"https://varantradarpro.pythonanywhere.com{ep}", timeout=20)
    print(f"{name:25}: Status {r.status_code} | {r.json().get('message', r.text[:60])}")
