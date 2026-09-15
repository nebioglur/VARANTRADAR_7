import os

with open('scanner/universal_scanner.py', 'r', encoding='utf-8') as f:
    text = f.read()

target = 'tech_result["v8_breakout"] = v8_breakout'
idx = text.find(target)
if idx != -1:
    insert = """
        # --- V8 EXECUTION ---
        try:
            from v8_engine.execution import ExecutionEngine
            exec_engine = ExecutionEngine()
            v8_exec = exec_engine.evaluate_entry(v8_breakout, regime)
        except Exception as e:
            v8_exec = {"entry_status": "ERROR"}
        tech_result["v8_execution"] = v8_exec
        # --------------------
"""
    if 'v8_execution =' not in text:
        text = text[:idx + len(target)] + "\n" + insert + text[idx + len(target):]
        with open('scanner/universal_scanner.py', 'w', encoding='utf-8') as f:
            f.write(text)
        print('Patched execution engine')
    else:
        print('Already patched')
else:
    print('Target not found')
