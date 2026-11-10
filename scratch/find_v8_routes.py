with open('server.py', 'r', encoding='utf-8', errors='ignore') as f:
    for idx, line in enumerate(f, 1):
        if '/api/v8/' in line:
            print(f"{idx}: {ascii(line.strip()[:100])}")
