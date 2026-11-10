with open('server.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if 'api_v8_market_regime' in l:
        print(f"Line {i+1}:")
        for j in range(i, min(len(lines), i+25)):
            print(f"{j+1}: {lines[j]}", end='')
        break
