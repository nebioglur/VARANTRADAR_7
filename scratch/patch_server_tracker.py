import os

with open('server.py', 'r', encoding='utf-8') as f:
    text = f.read()

target = "regime_engine = MarketRegimeEngine()"
idx = text.find(target)
if idx != -1:
    insert = """
        from v8_engine.learning import OutcomeEngine
        outcome_engine = OutcomeEngine()
        outcome_engine.run_outcome_tracker_loop()
"""
    if 'outcome_engine.run_outcome_tracker_loop()' not in text:
        text = text[:idx + len(target)] + "\n" + insert + text[idx + len(target):]
        with open('server.py', 'w', encoding='utf-8') as f:
            f.write(text)
        print('Tracker Thread patched in server.py')
    else:
        print('Already patched')
else:
    print('Target not found')
