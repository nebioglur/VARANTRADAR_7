import sys
with open('ui/app.js', 'r', encoding='utf-8') as f:
    c = f.read()
idx = c.find('function renderStatsMode')
sys.stdout.buffer.write(c[idx:idx+5500].encode('utf-8'))
