import sys, os
sys.path.insert(0, os.path.abspath('.'))

import server
import json

with open('dashboard_cache.json', 'r', encoding='utf-8') as f:
    server.GLOBAL_DASHBOARD_CACHE = json.load(f)

server.GLOBAL_DASHBOARD_CACHE['v8_market_regime'] = {
    'regime': 'BULL',
    'score': 65.0,
    'xu100_trend': 1.2,
    'volatility_state': 'NORMAL'
}

with server.app.test_request_context():
    res = server.api_v8_radar_breakout()
    data = res.get_json().get("data", [])
    print(f"Total breakout results: {len(data)}")
    statuses = {}
    for d in data:
        st = d.get("entry_status")
        statuses[st] = statuses.get(st, 0) + 1
    print("Statuses under BULL regime:", statuses)
    
    enter_items = [d for d in data if d.get("entry_status") == "ENTER"]
    print(f"ENTER count: {len(enter_items)}")
    for e in enter_items:
        print(f"  - {e.get('symbol')}: score={e.get('breakout_score')}, price={e.get('price')}, reasons={e.get('entry_reasons')}")
