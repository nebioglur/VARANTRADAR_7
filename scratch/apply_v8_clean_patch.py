import os, re

# 1. Update v8_engine/regime.py
with open('v8_engine/regime.py', 'r', encoding='utf-8', errors='ignore') as f:
    r_code = f.read()

if '_get_pa_proxy_session' not in r_code:
    proxy_helper = '''
def _get_pa_proxy_session():
    """PythonAnywhere free tier dis internet erisimi icin proxy oturumu dondurur."""
    import requests, os
    if os.path.exists("/home/varantradarpro") or "pythonanywhere" in os.environ.get("PYTHONANYWHERE_DOMAIN", "").lower() or os.path.exists("/etc/pythonanywhere"):
        session = requests.Session()
        session.proxies = {
            "http": "http://proxy.server:3128",
            "https": "http://proxy.server:3128"
        }
        return session
    return None
'''
    r_code = r_code.replace('from typing import Dict, Any', 'from typing import Dict, Any\n' + proxy_helper)
    r_code = r_code.replace('self.index_symbol = "XU100.IS"', 'self.index_symbol = "XU100.IS"\n        self._pa_session = _get_pa_proxy_session()')
    r_code = r_code.replace('yf.download(self.index_symbol, period="5d", interval="1h", progress=False)', 'yf.download(self.index_symbol, period="5d", interval="1h", progress=False, **({"session": self._pa_session} if self._pa_session else {}))')
    r_code = r_code.replace('yf.Ticker(self.index_symbol).history(period="5d", interval="1h")', 'yf.Ticker(self.index_symbol, **({"session": self._pa_session} if self._pa_session else {})).history(period="5d", interval="1h")')
    r_code = r_code.replace('yf.download(self.index_symbol, period="3mo", interval="1d", progress=False)', 'yf.download(self.index_symbol, period="3mo", interval="1d", progress=False, **({"session": self._pa_session} if self._pa_session else {}))')
    r_code = r_code.replace('yf.Ticker(self.index_symbol).history(period="3mo", interval="1d")', 'yf.Ticker(self.index_symbol, **({"session": self._pa_session} if self._pa_session else {})).history(period="3mo", interval="1d")')

    with open('v8_engine/regime.py', 'w', encoding='utf-8') as f:
        f.write(r_code)
    print('v8_engine/regime.py updated with proxy!')

# 2. Update v8_engine/execution.py
with open('v8_engine/execution.py', 'r', encoding='utf-8', errors='ignore') as f:
    e_code = f.read()

# Remove NEUTRAL return NO_ENTRY block
pattern = r'if market_regime == "NEUTRAL":\s+reasons\.append\([^)]+\)\s+return self\._build_result\([^)]+\)'
if re.search(pattern, e_code):
    e_code = re.sub(pattern, '# NEUTRAL rejimde elit kirilimlar kurallara gore degerlendirilir', e_code)
    with open('v8_engine/execution.py', 'w', encoding='utf-8') as f:
        f.write(e_code)
    print('v8_engine/execution.py updated: NEUTRAL gate relaxed!')
else:
    print('NEUTRAL pattern not found in execution.py')

# 3. Update server.py: threshold 5.0 -> 9.2 and dynamic evaluation
with open('server.py', 'r', encoding='utf-8', errors='ignore') as f:
    s_code = f.read()

if 'if chg >= 5.0:' in s_code:
    s_code = s_code.replace('if chg >= 5.0:', 'if chg >= 9.2:')
    print('server.py: ceiling threshold changed to 9.2%')

# Ensure breakout re-evaluates dynamically with ExecutionEngine
old_bo_block = '''            row["volume"] = data.get("Volume", 0)
            row["volume_strength"] = _stats_rel_vol(data)
            row["scan_timestamp"] = cache_ts
            row["entry_status"] = data.get("v8_execution", {}).get("entry_status", "UNKNOWN")
            row["entry_reasons"] = data.get("v8_execution", {}).get("reasons", [])
            breakout_list.append(_v8_gate_enter_row(row, sym, data))'''

new_bo_block = '''            row["volume"] = data.get("Volume", 0)
            row["volume_strength"] = _stats_rel_vol(data)
            row["scan_timestamp"] = cache_ts
            eval_res = _dyn_exec.evaluate_entry(bo, current_regime)
            row["entry_status"] = eval_res.get("entry_status", "UNKNOWN")
            row["entry_reasons"] = eval_res.get("reasons", [])
            row["momentum_speed"] = eval_res.get("momentum_speed", "NORMAL")
            row["timeframe_quality"] = eval_res.get("timeframe_quality", 0)
            breakout_list.append(_v8_gate_enter_row(row, sym, data))'''

if old_bo_block in s_code:
    s_code = s_code.replace(old_bo_block, new_bo_block)
    print('server.py: dynamic execution evaluation added to breakout loop!')

if 'current_regime = (GLOBAL_DASHBOARD_CACHE.get("v8_market_regime") or {}).get("regime", "NEUTRAL")' not in s_code:
    s_code = s_code.replace(
        'breakout_list = []\n    cache_ts = GLOBAL_DASHBOARD_CACHE.get("cache_timestamp")',
        'breakout_list = []\n    cache_ts = GLOBAL_DASHBOARD_CACHE.get("cache_timestamp")\n    current_regime = (GLOBAL_DASHBOARD_CACHE.get("v8_market_regime") or {}).get("regime", "NEUTRAL")\n    from v8_engine.execution import ExecutionEngine as _DynExecEngine\n    _dyn_exec = _DynExecEngine()'
    )
    print('server.py: _DynExecEngine initialized!')

with open('server.py', 'w', encoding='utf-8') as f:
    f.write(s_code)
print('server.py updated successfully!')
