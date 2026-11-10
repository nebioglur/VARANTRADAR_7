with open('v8_engine/regime.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for j in range(20, 60):
    print(f"{j+1}: {lines[j]}", end='')
