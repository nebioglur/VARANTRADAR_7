import sys
with open('ui/app.js', 'r', encoding='utf-8') as f:
    c = f.read()
idx = c.find("if (current_stats_mode === 'daily')")
sys.stdout.buffer.write(c[idx:idx+1500].encode('utf-8'))
