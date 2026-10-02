# -*- coding: utf-8 -*-
with open('scanner/universal_scanner.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_dict = '''                all_symbols_stats[sym] = {
                    "Daily_EMA50": r["Daily_EMA50"],
                    "Daily_EMA200": r["Daily_EMA200"],
                    "Daily_Close": r["Daily_Close"],
                    "Price": r.get("Price"),
                    "High": r.get("High"),
                    "Low": r.get("Low")
                }'''

new_dict = '''                all_symbols_stats[sym] = {
                    "Daily_EMA50": r["Daily_EMA50"],
                    "Daily_EMA200": r["Daily_EMA200"],
                    "Daily_Close": r["Daily_Close"],
                    "Price": r.get("Price"),
                    "High": r.get("High"),
                    "Low": r.get("Low"),
                    "Change_Pct": r.get("Change_Pct", 0.0),
                    "Volume": r.get("Volume", 0),
                    "Time": r.get("Time", "-"),
                    "v8_discovery": r.get("v8_discovery"),
                    "v8_breakout": r.get("v8_breakout"),
                    "v8_execution": r.get("v8_execution"),
                    "v8_varrant": r.get("v8_varrant")
                }'''

content = content.replace(old_dict, new_dict)

with open('scanner/universal_scanner.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("SCANNER YAZILDI")
