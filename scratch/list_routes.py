import re

with open('server.py', 'r', encoding='utf-8') as f:
    text = f.read()

routes = re.findall(r'@app\.route\(([\'"][^\'"]+[\'"])', text)
for r in routes:
    clean_r = r.strip('\'"')
    if any(k in clean_r for k in ['v8', 'simulation', 'telegram', 'apk', 'trade', 'backtest']):
        print(clean_r)
