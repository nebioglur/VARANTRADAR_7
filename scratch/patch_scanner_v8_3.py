import os

with open('scanner/universal_scanner.py', 'r', encoding='utf-8') as f:
    text = f.read()

target = "return tech_result"
idx = text.find(target, text.find('def _process_bulk_df'))
if idx != -1:
    insert = """
        # --- V8 DISCOVERY ---
        try:
            from v8_engine.discovery import DiscoveryEngine
            disc_engine = DiscoveryEngine()
            v8_disc = disc_engine.analyze_preparation(df, symbol)
        except Exception as e:
            v8_disc = {"state": "ERROR", "preparation_score": 0, "reasons": []}
        tech_result["v8_discovery"] = v8_disc
        # --------------------
"""
    if 'v8_disc =' not in text:
        text = text[:idx] + insert + "\n        " + text[idx:]
        with open('scanner/universal_scanner.py', 'w', encoding='utf-8') as f:
            f.write(text)
        print('Patched universal_scanner.py')
    else:
        print('Already patched')
else:
    print('Target not found')
