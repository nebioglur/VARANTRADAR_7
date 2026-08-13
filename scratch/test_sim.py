import requests
import json

try:
    res = requests.get('http://127.0.0.1:5000/api/simulation/daily_pnl')
    data = res.json()
    print(json.dumps(data, indent=2))
except Exception as e:
    print("Error:", str(e))
