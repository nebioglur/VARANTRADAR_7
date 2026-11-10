import sys
import difflib
sys.stdout.reconfigure(encoding='utf-8')

with open('ui/app.js', 'r', encoding='utf-8', errors='ignore') as f1, open('pro8_app.js', 'r', encoding='utf-8', errors='ignore') as f2:
    lines1 = f1.readlines()
    lines2 = f2.readlines()

print(f"ui/app.js: {len(lines1)} lines")
print(f"pro8_app.js: {len(lines2)} lines")

matcher = difflib.SequenceMatcher(None, lines1, lines2)
for tag, i1, i2, j1, j2 in matcher.get_opcodes():
    if tag != 'equal':
        print(f"\n[{tag}] ui/app.js lines {i1+1}-{i2} vs pro8_app.js lines {j1+1}-{j2}:")
        if i2 - i1 <= 10 and j2 - j1 <= 10:
            for l in lines1[i1:i2]:
                print(f"  - {l.strip()}")
            for l in lines2[j1:j2]:
                print(f"  + {l.strip()}")
        else:
            print(f"  ui/app.js has {i2-i1} lines, pro8_app.js has {j2-j1} lines")
            print("  First line of ui/app.js:", repr(lines1[i1].strip() if i1 < len(lines1) else ''))
            print("  First line of pro8_app.js:", repr(lines2[j1].strip() if j1 < len(lines2) else ''))
