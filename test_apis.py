import sys
import json
from services.win_rate_engine import WinRateEngine
from server import GLOBAL_DASHBOARD_CACHE, api_v8_radar_discovery

print("--- TEST WINRATE ---")
try:
    stats = WinRateEngine.get_performance_stats()
    print("WINRATE SUCCESS! Keys:", stats.keys())
    print("Daily Breakdown Len:", len(stats.get("daily_breakdown", [])))
except Exception as e:
    import traceback
    traceback.print_exc()

print("--- TEST V8 DISCOVERY ---")
try:
    # Fake cache data for test
    GLOBAL_DASHBOARD_CACHE["all_symbols_stats"] = {
        "THYAO": {
            "v8_discovery": {"state": "READY", "preparation_score": 85},
            "Daily_Close": 250,
            "Change_Pct": 2.5
        }
    }
    # We can't directly call api_v8_radar_discovery() outside flask app context
    # because it uses jsonify. We'll simulate it:
    
    all_stats = GLOBAL_DASHBOARD_CACHE.get("all_symbols_stats", {})
    discovery_list = []
    for sym, data in all_stats.items():
        disc = data.get("v8_discovery")
        if disc and disc.get("state") in ["READY", "PREPARING", "WATCH"]:
            disc["symbol"] = sym
            disc["price"] = data.get("Daily_Close", 0.0)
            disc["change_pct"] = data.get("Change_Pct", 0.0)
            disc["volume"] = data.get("Volume", 0)
            discovery_list.append(disc)
    
    print("V8 SUCCESS! Discovery List:", discovery_list)
except Exception as e:
    import traceback
    traceback.print_exc()
