import sys, os
sys.path.insert(0, os.path.abspath('.'))
sys.stdout.reconfigure(encoding='utf-8')

from server import app

client = app.test_client()

with client.session_transaction() as sess:
    sess['logged_in'] = True
    sess['user'] = 'test_user'

endpoints = [
    '/api/v8/market/regime',
    '/api/v8/radar/breakout',
    '/api/v8/radar/discovery',
    '/api/v8/learning/outcomes',
]

for ep in endpoints:
    print(f"Testing {ep} ...")
    try:
        res = client.get(ep)
        print(f"Status: {res.status_code}")
        data = res.get_json()
        if data:
            print("Status in JSON:", data.get("status"))
            if "data" in data:
                items = data["data"]
                print(f"Data type: {type(items)}, length: {len(items) if isinstance(items, list) else 'dict'}")
                if isinstance(items, list) and items:
                    print("Sample item 0:", {k: items[0][k] for k in list(items[0].keys())[:6]})
            if "summary" in data:
                print("Summary:", data["summary"])
            if ep == '/api/v8/market/regime':
                print("Regime:", data.get("regime"), "Score:", data.get("score"), "Trend:", data.get("xu100_trend"))
        else:
            print("Response:", res.data[:200])
    except Exception as e:
        print("ERROR:", e)
    print("-" * 50)
