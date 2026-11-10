with open('server.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if 'v8_market_regime' in l and '=' in l:
        print(f"Line {i+1}: {l.strip()}")
        for j in range(max(0, i-2), min(len(lines), i+8)):
            print(f"  {j+1}: {lines[j]}", end='')
        print("="*40)
