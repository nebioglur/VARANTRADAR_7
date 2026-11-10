import subprocess

res = subprocess.check_output(['git', 'show', '413e560~1:ui/index.html'], encoding='utf-8', errors='ignore')
lines = res.splitlines()

start = None
end = None
for i, l in enumerate(lines):
    if 'id="v8-wrapper"' in l or 'id="v8"' in l:
        start = i
    if start is not None and i > start and 'id="logs-wrapper"' in l or (start is not None and i > start and 'id="guide-wrapper"' in l):
        end = i
        break

if start:
    print(f"V8 wrapper from line {start+1} to {end or len(lines)}:")
    for j in range(start, min(end or len(lines), start + 120)):
        print(f"{j+1}: {ascii(lines[j])}")
