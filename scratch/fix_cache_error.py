import os

with open('server.py', 'r', encoding='utf-8') as f:
    text = f.read()

# Replace the problematic lines in load_dashboard_cache
target = 'if GLOBAL_DASHBOARD_CACHE.get("cache_date", today_str) != today_str:\n                GLOBAL_DASHBOARD_CACHE = {}'
replace_with = 'if data.get("cache_date", today_str) != today_str:\n                pass'

if target in text:
    text = text.replace(target, replace_with)
    with open('server.py', 'w', encoding='utf-8') as f:
        f.write(text)
    print("Fixed cache bug")
else:
    # Maybe indentation is different
    target2 = 'if GLOBAL_DASHBOARD_CACHE.get("cache_date", today_str) != today_str:'
    if target2 in text:
        # manual replace
        lines = text.split('\n')
        out_lines = []
        for i, line in enumerate(lines):
            if 'if GLOBAL_DASHBOARD_CACHE.get("cache_date", today_str) != today_str:' in line:
                out_lines.append(line.replace('GLOBAL_DASHBOARD_CACHE.get', 'data.get'))
            elif 'GLOBAL_DASHBOARD_CACHE = {}' in line and i > 50 and i < 150: # roughly in load_dashboard_cache
                out_lines.append(line.replace('GLOBAL_DASHBOARD_CACHE = {}', 'pass'))
            else:
                out_lines.append(line)
        with open('server.py', 'w', encoding='utf-8') as f:
            f.write('\n'.join(out_lines))
        print("Fixed cache bug (fallback)")
    else:
        print("Target not found")
