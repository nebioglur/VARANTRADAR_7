with open('server.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()
for l in [442, 529, 537, 578, 599, 613, 720, 830, 897]:
    print(f"Line {l}:")
    for j in range(max(0, l-2), min(l+5, len(lines))):
        print(f"  {j}: {lines[j].strip()}")
