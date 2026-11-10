with open('ui/index.html', encoding='utf-8') as f:
    for idx, line in enumerate(f):
        if 'switchMainTab' in line or 'id="v8' in line:
            print(f'{idx+1}: {line.strip()[:100]}')
