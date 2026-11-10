with open('ui/index.html', 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if 'id="v8-wrapper"' in l or 'id="v8"' in l or 'id="v8_wrapper"' in l:
        print(f"Match line {i+1}: {l.strip()[:100]}")
        for j in range(i, min(len(lines), i+60)):
            print(f"  {j+1}: {ascii(lines[j].strip()[:100])}")
        print("="*40)
