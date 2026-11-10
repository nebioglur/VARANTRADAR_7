import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('ui/app.js', 'r', encoding='utf-8') as f:
    text = f.read()

idx2 = 226478
print(text[idx2+800:idx2+2200])
