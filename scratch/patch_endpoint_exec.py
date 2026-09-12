import os

with open('server.py', 'r', encoding='utf-8') as f:
    text = f.read()

target = 'bo["volume"] = data.get("Volume", 0)'
replace_with = 'bo["volume"] = data.get("Volume", 0)\n            bo["entry_status"] = data.get("v8_execution", {}).get("entry_status", "UNKNOWN")\n            bo["entry_reasons"] = data.get("v8_execution", {}).get("reasons", [])'

if target in text and 'entry_status' not in text[text.find(target):text.find(target)+200]:
    text = text.replace(target, replace_with)
    with open('server.py', 'w', encoding='utf-8') as f:
        f.write(text)
    print('Execution attached to endpoint')
else:
    print('Target not found or already patched')
