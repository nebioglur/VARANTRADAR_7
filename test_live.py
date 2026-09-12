import requests

try:
    r = requests.get("https://varantradar-7.onrender.com/api/winrate_stats")
    print("STATUS:", r.status_code)
    print("RESPONSE:", r.text[:500])
except Exception as e:
    print("ERR:", e)
