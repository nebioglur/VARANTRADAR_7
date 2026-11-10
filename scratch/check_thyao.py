import json

with open('dashboard_cache.json', encoding='utf-8') as f:
    dash = json.load(f)

stats = dash.get('all_symbols_stats', {})
thyao = stats.get('THYAO.IS', {})
print("THYAO Price_Stale:", thyao.get('Price_Stale'))
print("THYAO v8_breakout:", thyao.get('v8_breakout'))
print("THYAO v8_execution:", thyao.get('v8_execution'))
print("THYAO Change_Pct:", thyao.get('Change_Pct'))
