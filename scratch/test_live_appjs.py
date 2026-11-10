from selenium import webdriver
from selenium.webdriver.edge.options import Options
import os

opts = Options()
opts.add_argument('--headless')
opts.add_argument('--disable-gpu')
opts.set_capability('ms:loggingPrefs', {'browser': 'ALL'})
opts.set_capability('goog:loggingPrefs', {'browser': 'ALL'})

driver = webdriver.Edge(options=opts)

# Create full dummy DOM
html_content = '''<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body>
    <input id="symbol-input" />
    <div id="ac-dropdown"></div>
    <div id="live-clock">00:00:00</div>
    <div id="live-date">GÜN AY YIL</div>
    <div id="v8-sectors-text"></div>
    <div id="v8-regime-text"></div>
    <div id="v8-playbook-strip"></div>
    <script src="../ui/app.js"></script>
</body>
</html>'''

with open('scratch/test_full_dom.html', 'w', encoding='utf-8') as f:
    f.write(html_content)

file_url = 'file:///' + os.path.abspath('scratch/test_full_dom.html').replace('\\', '/')
driver.get(file_url)

logs = driver.get_log('browser')
print(f"Total browser logs: {len(logs)}")
syntax_errors = []
for l in logs:
    lvl = l.get('level')
    msg = l.get('message')
    print(f"[{lvl}] {msg}")
    if 'SyntaxError' in msg:
        syntax_errors.append(msg)

driver.quit()
if syntax_errors:
    print("\nFAILED: SyntaxError found:")
    for e in syntax_errors:
        print(" ", e)
    exit(1)
else:
    print("\nSUCCESS: 100% CLEAN SYNTAX! NO SYNTAX ERRORS AT ALL!")
