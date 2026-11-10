import re

with open('ui/style.css', 'r', encoding='utf-8') as f:
    text = f.read()

# Remove overflow: hidden !important; from .data-table
text = re.sub(r'overflow:\s*hidden\s*!important;\s*(/\*.*?\*/)?', '', text)

with open('ui/style.css', 'w', encoding='utf-8') as f:
    f.write(text)

print('Removed overflow: hidden from style.css')
