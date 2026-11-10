import os
from selenium import webdriver
from selenium.webdriver.edge.options import Options

opts = Options()
opts.add_argument('--headless')
opts.add_argument('--disable-gpu')
opts.set_capability('ms:loggingPrefs', {'browser': 'ALL'})
opts.set_capability('goog:loggingPrefs', {'browser': 'ALL'})

driver = webdriver.Edge(options=opts)
file_url = 'file:///' + os.path.abspath('scratch/test_syntax.html').replace('\\', '/')
print('Loading', file_url)
driver.get(file_url)

logs = driver.get_log('browser')
print(f'Browser logs count: {len(logs)}')
severe_errors = []
for l in logs:
    lvl = l.get('level')
    msg = l.get('message')
    print(f"[{lvl}] {msg}")
    if lvl == 'SEVERE' and 'SyntaxError' in msg:
        severe_errors.append(msg)

driver.quit()
if severe_errors:
    print('FAILED: Syntax errors found!')
    exit(1)
else:
    print('SUCCESS: ZERO SYNTAX ERRORS IN UI/APP.JS!')
