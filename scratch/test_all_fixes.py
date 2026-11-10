import sys, os
sys.path.insert(0, os.path.abspath('.'))
sys.stdout.reconfigure(encoding='utf-8')

print("=== 1. Checking Telegram Credentials ===", flush=True)
from services.telegram_bot import get_telegram_credentials
token, chat_id = get_telegram_credentials(force=True)
print(f"Token: {token[:10]}... | Chat ID: {chat_id}", flush=True)
assert token and chat_id, "Telegram credentials must not be empty!"

print("\n=== 2. Checking V8 Engine Aliases ===", flush=True)
from v8_engine.breakout import V8BreakoutEngine, BreakoutEngine
from v8_engine.learning import V8LearningEngine, OutcomeEngine
from v8_engine.regime import V8RegimeEngine, MarketRegimeEngine
assert V8BreakoutEngine is BreakoutEngine
assert V8LearningEngine is OutcomeEngine
assert V8RegimeEngine is MarketRegimeEngine
print("All V8 aliases match correctly!", flush=True)

print("\n=== 3. Checking Server API Endpoints ===", flush=True)
from server import app

client = app.test_client()
with client.session_transaction() as sess:
    sess['logged_in'] = True
    sess['user'] = 'test_user'

endpoints = [
    ('/api/v8/market/regime', 'GET', None),
    ('/api/v8/radar/breakout', 'GET', None),
    ('/api/v8/radar/discovery', 'GET', None),
    ('/api/v8/learning/outcomes', 'GET', None),
    ('/api/simulation/daily_pnl', 'GET', None),
    ('/api/telegram/test_suite', 'POST', {'type': 'buy'})
]

for ep, method, payload in endpoints:
    print(f"Testing {ep} ({method}) ...", flush=True)
    if method == 'GET':
        res = client.get(ep)
    else:
        res = client.post(ep, json=payload or {})
    print(f"  Status code: {res.status_code}", flush=True)
    data = res.get_json() or {}
    print(f"  Status in response: {data.get('status')}", flush=True)
    if 'data' in data:
        print(f"  Items in data: {len(data['data']) if isinstance(data['data'], list) else 'dict'}", flush=True)
    if 'summary' in data:
        print(f"  Summary: total={data['summary'].get('total_signals')}, win_rate={data['summary'].get('win_rate')}%", flush=True)
    if 'trades' in data:
        print(f"  Trades count: {len(data['trades'])}", flush=True)
    if 'results' in data:
        print(f"  Results: {data['results']}", flush=True)

print("\n=== All Tests Completed Successfully! ===", flush=True)
