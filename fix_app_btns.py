import re

with open('ui/app.js', 'r', encoding='utf-8') as f:
    text = f.read()

# For Tavan Radar Action Buttons
text = re.sub(
    r'(let actionBtns = \')(<button.*?D/D</button>\';)',
    r'\1<div style="white-space:nowrap; display:flex; gap:4px; align-items:center;">\2</div>\';',
    text,
    flags=re.DOTALL
)

# Also fix the All Stocks Action Buttons (if it uses different quotes)
text = text.replace(
    '''let actionBtns = <button''',
    '''let actionBtns = <div style="white-space:nowrap; display:flex; gap:4px; align-items:center;"><button'''
)
text = text.replace(
    '''D/D</button>;''',
    '''D/D</button></div>;'''
)


with open('ui/app.js', 'w', encoding='utf-8') as f:
    f.write(text)

print('Patched app.js for white-space nowrap on buttons')
