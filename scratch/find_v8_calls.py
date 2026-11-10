with open('ui/app.js', 'r', encoding='utf-8', errors='ignore') as f:
    for idx, line in enumerate(f, 1):
        if 'loadV8Playbook' in line or 'loadV8Weekly' in line:
            print(f"{idx}: {ascii(line.strip()[:100])}")
