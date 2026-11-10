import json

with open('dashboard_cache.json', encoding='utf-8') as f:
    dash = json.load(f)

acsel = dash.get("all_symbols_stats", {}).get("ACSEL.IS", {})
print("ACSEL Price_Stale:", acsel.get("Price_Stale"))
print("ACSEL v8_breakout:", acsel.get("v8_breakout"))
print("ACSEL v8_execution:", acsel.get("v8_execution"))
print("ACSEL Change_Pct:", acsel.get("Change_Pct"))
