import os

with open('scanner/universal_scanner.py', 'r', encoding='utf-8') as f:
    text = f.read()

target = 'tech_result["v8_execution"] = v8_exec'
idx = text.find(target)
if idx != -1:
    insert = """
        # --- V8 VARIANT SELECTION ---
        try:
            from v8_engine.varrant import VarrantEngine
            var_engine = VarrantEngine()
            # Eger giris karari ciktiysa varant oner
            if v8_exec.get("entry_status") in ["ENTER", "WAIT_PULLBACK"]:
                v8_varrant = var_engine.find_best_varrant(symbol, "CALL")
            else:
                v8_varrant = {"status": "NO_ENTRY_SIGNAL"}
        except Exception as e:
            v8_varrant = {"status": "ERROR"}
        tech_result["v8_varrant"] = v8_varrant
        # ----------------------------
"""
    if 'v8_varrant =' not in text:
        text = text[:idx + len(target)] + "\n" + insert + text[idx + len(target):]
        with open('scanner/universal_scanner.py', 'w', encoding='utf-8') as f:
            f.write(text)
        print('Patched Varrant Engine')
    else:
        print('Already patched')
else:
    print('Target not found')
