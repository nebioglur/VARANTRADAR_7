import re

for filename in ['ui/app.js', 'live_app.js']:
    with open(filename, 'r', encoding='utf-8') as f:
        content = f.read()

    # Replace the color logic
    content = re.sub(
        r"const closeColor = h\.avg_close_gain >= 0 \? 'var\(--accent-green\)' : 'var\(--accent-red\)';",
        r"const avgMax = h.avg_max_gain_pct || 0;\n                    const avgClose = h.avg_closing_gain_pct || 0;\n                    const closeColor = avgClose >= 0 ? 'var(--accent-green)' : 'var(--accent-red)';",
        content
    )
    content = re.sub(
        r"const closeSign = h\.avg_close_gain >= 0 \? '\+' : '';",
        r"const closeSign = avgClose >= 0 ? '+' : '';",
        content
    )
    # Remove the ones we added earlier to avoid duplicates
    content = re.sub(r"const avgMax = h\.avg_max_gain_pct \|\| 0;\s*const avgClose = h\.avg_closing_gain_pct \|\| 0;\s*tr\.innerHTML = `", r"tr.innerHTML = `", content)

    with open(filename, 'w', encoding='utf-8') as f:
        f.write(content)
        
print("Fixed avgClose logic")
