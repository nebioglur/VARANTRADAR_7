with open('ui/app.js', 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

for idx in range(6340, 6450):
    print(f"{idx+1}: {ascii(lines[idx])}")
