import json
import sys

# Test server.py's api_v8_radar_breakout logic directly
# We can import server or replicate it exactly:
with open('server.py', 'r', encoding='utf-8') as f:
    code = f.read()

# Let's extract api_v8_radar_breakout
start = code.find("def api_v8_radar_breakout():")
end = code.find("def api_v8_radar_discovery():")
func_code = code[start:end]

with open('scratch/test_server_func.py', 'w', encoding='utf-8') as f:
    f.write('''import json
CACHE_FILE = "dashboard_cache.json"
GLOBAL_DASHBOARD_CACHE = {}
''')
    # include helper functions
    for helper in ['_v8_live_price', '_stats_rel_vol', '_v8_gate_enter_row', '_v8_regime_locked', '_v8_defense_mode_check', '_v8_kap_news_gate', '_v8_a_class_gate', '_v8_tplus3_confirmation_gate']:
        h_start = code.find(f"def {helper}(")
        if h_start != -1:
            h_end = code.find("\ndef ", h_start + 1)
            f.write(code[h_start:h_end] + "\n\n")

    f.write('''
def jsonify(x): return x

''' + func_code + '''

res = api_v8_radar_breakout()
data = res['data']
from collections import Counter
counts = Counter(x.get('entry_status') for x in data)
print("Current server.py counts:", counts)
waits = [x.get('symbol') for x in data if x.get('entry_status') == 'WAIT']
print(f"WAIT symbols count {len(waits)}: {waits[:15]}")
''')
