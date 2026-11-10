with open('ui/app.js', 'r', encoding='utf-8', errors='ignore') as f:
    app_lines = f.readlines()

for i, line in enumerate(app_lines):
    if 'navClick' in line or 'location.hash' in line or 'hashchange' in line or 'DOMContentLoaded' in line:
        print(f"app.js Line {i+1}: {line.strip()[:100]}")

with open('ui/index.html', 'r', encoding='utf-8', errors='ignore') as f:
    html_lines = f.readlines()

for i, line in enumerate(html_lines):
    if 'navClick' in line or 'location.hash' in line or 'hashchange' in line:
        print(f"index.html Line {i+1}: {line.strip()[:100]}")
