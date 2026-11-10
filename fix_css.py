import re

with open('ui/style.css', 'r', encoding='utf-8') as f:
    text = f.read()

# Make sure table-scroll-wrapper has overflow-x: auto everywhere
text = text.replace('.table-scroll-wrapper { position: relative; }', '.table-scroll-wrapper { position: relative; overflow-x: auto; width: 100%; }')

with open('ui/style.css', 'w', encoding='utf-8') as f:
    f.write(text)

print('Patched style.css for horizontal scrolling')
