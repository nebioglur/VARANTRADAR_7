import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('ui/index.html', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

# find home-wrapper
start = text.find('id="home-wrapper"')
if start == -1:
    start = text.find("id='home-wrapper'")

print("Start of home-wrapper:", start)
# find the corresponding end or next main-wrapper
end = text.find('class="main-wrapper"', start + 25)
print("Next main-wrapper at:", end)

home_html = text[start-10:end]
print(f"home-wrapper HTML length: {len(home_html)}")
print("\n--- FIRST 2000 CHARS ---")
print(home_html[:2000])

print("\n--- LAST 2000 CHARS ---")
print(home_html[-2000:])
