import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('ui/index.html', 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

stack = []
for i in range(157, 588):
    line = lines[i]
    import re
    # find divs
    tokens = re.findall(r'(</?div[^>]*>)', line)
    for t in tokens:
        if t.startswith('</'):
            if stack:
                top_line, top_t = stack.pop()
                print(f"L{i+1}: Closes div from L{top_line}: {top_t[:40]}")
            else:
                print(f"L{i+1}: EXTRA closing div! {t}")
        else:
            stack.append((i+1, t))

print("\nRemaining unclosed divs in stack:", len(stack))
for l, t in stack:
    print(f"  Unclosed from L{l}: {t[:40]}")
