from selenium import webdriver
from selenium.webdriver.edge.options import Options

opts = Options()
opts.add_argument('--headless')
opts.add_argument('--disable-gpu')
driver = webdriver.Edge(options=opts)
driver.get('about:blank')

with open('ui/app.js', 'r', encoding='utf-8') as f:
    lines = f.readlines()

def test_code(code_str):
    res = driver.execute_script('''
        try {
            new Function(arguments[0]);
            return null;
        } catch(e) {
            return e.message;
        }
    ''', code_str)
    return res

# Binary search the lines
low = 1
high = len(lines)
err_line = -1

print(f"Total lines: {len(lines)}")
# Check line by line or find functions
# Let's test top-level blocks or binary search by line prefixes (if closing with dummy braces)
# Or even better: extract each top-level function and test it!

import re

# Split by function / top-level statements
for i in range(100, len(lines), 200):
    chunk = "".join(lines[:i])
    # Try closing open braces
    open_b = chunk.count('{') - chunk.count('}')
    open_p = chunk.count('(') - chunk.count(')')
    test_chunk = chunk + (")" * max(0, open_p)) + ("}" * max(0, open_b))
    err = test_code(test_chunk)
    # If error is specifically "missing ) after argument list"
    if err and "missing ) after argument list" in err:
        print(f"Found error in first {i} lines! Binary searching between {i-200} and {i}...")
        for j in range(max(1, i-200), i+1):
            chunk2 = "".join(lines[:j])
            ob = chunk2.count('{') - chunk2.count('}')
            op = chunk2.count('(') - chunk2.count(')')
            tc = chunk2 + (")" * max(0, op)) + ("}" * max(0, ob))
            err2 = test_code(tc)
            if err2 and "missing ) after argument list" in err2:
                print(f"First trigger at line {j}:")
                for k in range(max(0, j-5), min(len(lines), j+5)):
                    print(f"{k+1}: {lines[k].rstrip()}")
                break
        break

driver.quit()
