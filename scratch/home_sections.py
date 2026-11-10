import re
import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('ui/index.html', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

start = text.find('id="home-wrapper"')
end = text.find('class="main-wrapper"', start + 25)
home_html = text[start:end]

headings = re.findall(r'(<(?:h[1-6]|summary)[^>]*>.*?</(?:h[1-6]|summary)>)', home_html, re.I | re.DOTALL)
for h in headings:
    clean = re.sub(r'<[^>]+>', '', h).strip()
    print("Heading:", clean)

tables = re.findall(r'<table[^>]*id=["\']([^"\']+)["\']', home_html, re.I)
print("\nTables in home-wrapper:", tables)

buttons = re.findall(r'<button[^>]*onclick=["\']([^"\']+)["\']', home_html, re.I)
print("\nButtons onclick count:", len(buttons))
for b in buttons[:20]:
    print("  button onclick:", b)
