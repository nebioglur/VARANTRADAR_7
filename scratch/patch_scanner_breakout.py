import os

with open('scanner/universal_scanner.py', 'r', encoding='utf-8') as f:
    text = f.read()

target = 'tech_result["v8_discovery"] = v8_disc'
idx = text.find(target)
if idx != -1:
    insert = """
        # --- V8 BREAKOUT ---
        try:
            from v8_engine.breakout import BreakoutEngine
            bo_engine = BreakoutEngine()
            try:
                import server
                regime = server.GLOBAL_DASHBOARD_CACHE.get("v8_market_regime", {}).get("regime", "NEUTRAL")
            except:
                regime = "NEUTRAL"
            v8_breakout = bo_engine.analyze_breakout(df, symbol, regime)
        except Exception as e:
            v8_breakout = {"is_breakout": False, "status": "ERROR"}
        tech_result["v8_breakout"] = v8_breakout
        # -------------------
"""
    if 'v8_breakout =' not in text:
        text = text[:idx + len(target)] + "\n" + insert + text[idx + len(target):]
        with open('scanner/universal_scanner.py', 'w', encoding='utf-8') as f:
            f.write(text)
        print('Patched breakout engine')
    else:
        print('Already patched')
else:
    print('Target not found')
