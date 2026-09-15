with open('ui/app.js', 'r', encoding='utf-8') as f:
    content = f.read()

old = ' Adet (%)'
new = '</td>\n                            <td style="color:var(--accent-green); font-weight:bold;"> Tavan (%)</td>\n                            <td style="color:var(--accent-blue); font-weight:bold;"> Adet (%)'
content = content.replace(old, new)
content = content.replace('+%', '+%')
content = content.replace('%', '%')

with open('ui/app.js', 'w', encoding='utf-8') as f:
    f.write(content)
print('Done')
