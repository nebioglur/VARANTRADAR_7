with open('ui/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

target = 'app.js?v=20261106_v37'
replacement = 'app.js?v=20261109_v38'

if target in text:
    text = text.replace(target, replacement, 1)
    with open('ui/index.html', 'w', encoding='utf-8') as f:
        f.write(text)
    print("BUMPED_APP_JS_CACHE_BUSTER")
else:
    print("NOT_FOUND")
