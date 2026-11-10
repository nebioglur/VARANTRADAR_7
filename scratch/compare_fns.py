import sys
import re
sys.stdout.reconfigure(encoding='utf-8')

def extract_functions(filepath):
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        text = f.read()
    fns = set(re.findall(r'(?:async\s+)?function\s+([a-zA-Z0-9_$]+)', text))
    fns.update(re.findall(r'window\.([a-zA-Z0-9_$]+)\s*=\s*(?:async\s+)?function', text))
    return fns

fns_main = extract_functions('ui/app.js')
fns_pro8 = extract_functions('pro8_app.js')

print(f"Total fns in ui/app.js: {len(fns_main)}")
print(f"Total fns in pro8_app.js: {len(fns_pro8)}")

in_main_not_pro8 = fns_main - fns_pro8
in_pro8_not_main = fns_pro8 - fns_main

print("\n--- Functions in local ui/app.js but MISSING in deployed pro8_app.js ---")
for f in sorted(in_main_not_pro8):
    print(" ", f)

print("\n--- Functions in deployed pro8_app.js but MISSING in local ui/app.js ---")
for f in sorted(in_pro8_not_main):
    print(" ", f)
