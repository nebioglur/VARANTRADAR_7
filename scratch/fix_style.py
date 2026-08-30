import sys
with open('ui/style.css', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('--bg-base: #0B1120;', '--bg-base: #131314;')
content = content.replace('--bg-card: rgba(30, 41, 59, 0.6);', '--bg-card: rgba(30, 30, 30, 0.6);')
content = content.replace('--bg-card-hover: rgba(51, 65, 85, 0.8);', '--bg-card-hover: rgba(50, 50, 50, 0.8);')

with open('ui/style.css', 'w', encoding='utf-8') as f:
    f.write(content)
print('Style updated!')
