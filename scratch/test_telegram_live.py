import requests
import json

s = requests.Session()
s.headers.update({"User-Agent": "AuditBot/1.0"})

r_log = s.post("https://varantradarpro.pythonanywhere.com/login", json={"username": "nebioglur", "password": "123"})
print("Login status:", r_log.status_code)

# 1. Telegram Settings
r_set = s.get("https://varantradarpro.pythonanywhere.com/api/telegram/settings")
print("Settings:", r_set.json())

# 2. Test Message
try:
    r_test = s.post("https://varantradarpro.pythonanywhere.com/api/telegram/test", timeout=10)
    print("Test Message Endpoint:", r_test.status_code, r_test.json())
except Exception as e:
    print("Test Message Error:", e)

# 3. Dag Kekligi (Tavan adaylari)
try:
    r_dk = s.post("https://varantradarpro.pythonanywhere.com/api/telegram/send_tavan_candidates", timeout=10)
    print("Send Tavan Candidates Endpoint:", r_dk.status_code, r_dk.json())
except Exception as e:
    print("Send Tavan Candidates Error:", e)

# 4. Ozel Siralama (Special ranking)
try:
    r_sr = s.post("https://varantradarpro.pythonanywhere.com/api/telegram/send_special_ranking", timeout=10)
    print("Send Special Ranking Endpoint:", r_sr.status_code, r_sr.json())
except Exception as e:
    print("Send Special Ranking Error:", e)

# 5. Gunun Pusulasi (Morning compass)
try:
    r_mc = s.post("https://varantradarpro.pythonanywhere.com/api/telegram/send_morning_compass", timeout=10)
    print("Send Morning Compass Endpoint:", r_mc.status_code, r_mc.json())
except Exception as e:
    print("Send Morning Compass Error:", e)
