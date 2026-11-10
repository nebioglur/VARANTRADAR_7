with open('ui/index.html', 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

for idx in range(2225, 2240):
    print(f"{idx+1}: {repr(lines[idx])}")
