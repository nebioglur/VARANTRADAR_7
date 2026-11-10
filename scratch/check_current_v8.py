with open('ui/index.html', 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if 'id="v8"' in l or 'id="v8-section"' in l or 'V8 ENGINE' in l:
        print(f"Around line {i+1}:")
        for j in range(max(0, i-5), min(len(lines), i+80)):
            print(f"{j+1}: {ascii(lines[j])}")
        break
