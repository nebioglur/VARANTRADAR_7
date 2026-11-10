with open('ui/index.html', 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

start = None
for i, l in enumerate(lines):
    if 'id="home-wrapper"' in l or "id='home-wrapper'" in l:
        start = i
        break

print(f"home-wrapper starts at line {start+1}")
if start is not None:
    for j in range(start, min(start + 150, len(lines))):
        print(f"{j+1}: {lines[j]}", end='')
