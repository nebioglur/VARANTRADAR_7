import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('ui/index.html', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

idx = text.find('dip-breakout-table')
print("dip-breakout-table index:", idx)
if idx != -1:
    print(text[idx-500:idx+1500])
