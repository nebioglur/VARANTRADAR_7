import re

with open('ui/app.js', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace(
    '''let actionBtns = <button onclick="quickTradeBuy''',
    '''let actionBtns = <div style="white-space:nowrap; display:flex; gap:4px; align-items:center;"><button onclick="quickTradeBuy'''
)

text = text.replace(
    '''nc Seviyeleri">D/D</button>;''',
    '''nc Seviyeleri">D/D</button></div>;'''
)

with open('ui/app.js', 'w', encoding='utf-8') as f:
    f.write(text)

print('Patched app.js backtick actionBtns')
