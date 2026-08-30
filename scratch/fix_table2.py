with open('ui/app.js', 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
skip = False
for line in lines:
    if '<td>${h.total_signals}</td>' in line:
        continue
    if '<td style="color:var(--accent-green); font-weight:bold;">${h.hit_ceiling} Tavan (%${h.tavan_rate})</td>' in line:
        continue
    new_lines.append(line)

with open('ui/app.js', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

with open('live_app.js', 'r', encoding='utf-8') as f:
    lines2 = f.readlines()
new_lines2 = []
for line in lines2:
    if '<td>${h.total_signals}</td>' in line:
        continue
    if '<td style="color:var(--accent-green); font-weight:bold;">${h.hit_ceiling} Tavan (%${h.tavan_rate})</td>' in line:
        continue
    new_lines2.append(line)
with open('live_app.js', 'w', encoding='utf-8') as f:
    f.writelines(new_lines2)
print("Removed old bugged columns")
