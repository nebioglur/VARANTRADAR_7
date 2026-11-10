with open('ui/app.js', 'r', encoding='utf-8', errors='ignore') as f:
    for idx, line in enumerate(f, 1):
        if 'v8-playbook-strip' in line or 'v8-weekly-strip' in line or 'runV8Backtest' in line:
            print(f"{idx}: {ascii(line.strip()[:100])}")
