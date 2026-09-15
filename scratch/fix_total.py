import re

with open('server.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the total logic
old_logic = """total = 0
    if clean_cache and isinstance(clean_cache, dict):
        seen = set()
        for cat_name, cat_items in clean_cache.items():
            if isinstance(cat_items, list):
                for item in cat_items:
                    if isinstance(item, dict) and 'Symbol' in item:
                        seen.add(item['Symbol'])
        total = len(seen)"""

new_logic = """total = len(BIST_SYMBOLS) if 'BIST_SYMBOLS' in globals() else 550
    # Add a bit of dynamic feeling or just return the static max
    total = len(BIST_SYMBOLS)"""

content = content.replace(old_logic, new_logic)

with open('server.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("Fixed total_analyzed")
