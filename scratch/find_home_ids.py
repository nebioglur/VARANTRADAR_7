import re
import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('ui/index.html', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

start = text.find('id="home-wrapper"')
end = text.find('class="main-wrapper"', start + 25)
home_html = text[start:end]

ids = re.findall(r'id=["\']([^"\']+)["\']', home_html)
print("Total IDs in home-wrapper:", len(ids))
for i in ids:
    print(" ", i)
