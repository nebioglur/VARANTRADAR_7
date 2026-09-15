import os

with open('server.py', 'r', encoding='utf-8') as f:
    text = f.read()

target = 'bo["entry_reasons"] = data.get("v8_execution", {}).get("reasons", [])'
replace_with = target + '\n            bo["varrant_info"] = data.get("v8_varrant", {})'

if target in text and 'varrant_info' not in text[text.find(target):text.find(target)+200]:
    text = text.replace(target, replace_with)
    with open('server.py', 'w', encoding='utf-8') as f:
        f.write(text)
    print('Varrant data attached to Breakout API')
else:
    print('Target not found or already patched')
