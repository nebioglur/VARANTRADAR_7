import re

with open('ui/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

# Add overflow-x: auto; to inline styles
text = text.replace('overflow-y:auto;', 'overflow-y:auto; overflow-x:auto;')
text = text.replace('overflow-y: auto;', 'overflow-y: auto; overflow-x: auto;')

with open('ui/index.html', 'w', encoding='utf-8') as f:
    f.write(text)

print('Patched index.html inline styles for overflow-x')
