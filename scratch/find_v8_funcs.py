with open('ui/app.js', 'r', encoding='utf-8') as f:
    text = f.read()

funcs = ['loadV8Regime', 'loadV8Discovery', 'loadV8Breakout', 'loadV8Learning']
for fn in funcs:
    idx = text.find(f'function {fn}')
    if idx != -1:
        print(f"=== {fn} ===")
        print(text[idx:idx+800])
        print("\n" + "="*40 + "\n")
