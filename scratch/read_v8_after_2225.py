with open('ui/index.html', 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

for idx in range(2225, min(len(lines), 2290)):
    print(f"{idx+1}: {ascii(lines[idx])}")
