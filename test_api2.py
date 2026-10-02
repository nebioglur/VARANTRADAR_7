from server import app
import json

with app.test_request_context('/api/simulation/daily_pnl'):
    from server import api_simulation_daily_pnl
    res = api_simulation_daily_pnl()
    with open("api_res.json", "w", encoding="utf-8") as f:
        json.dump(res.get_json(), f, ensure_ascii=False, indent=2)
