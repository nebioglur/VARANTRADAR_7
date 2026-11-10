with open('server.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if 'TAVAN RİSKİ KAPISI' in l:
        print(f"Line {i}:")
        for j in range(max(0, i-40), min(len(lines), i+30)):
            print(f"{j+1}: {lines[j]}", end='')
        break
