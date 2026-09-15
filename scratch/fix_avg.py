import sys

for filename in ['ui/app.js', 'live_app.js']:
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Replace the missing variable declarations
        old_str = "const closeSign = h.avg_close_gain >= 0 ? '+' : '';\n\n                    tr.innerHTML = `"
        new_str = "const closeSign = h.avg_close_gain >= 0 ? '+' : '';\n                    const avgMax = h.avg_max_gain_pct || 0;\n                    const avgClose = h.avg_closing_gain_pct || 0;\n\n                    tr.innerHTML = `"
        
        if old_str in content:
            content = content.replace(old_str, new_str)
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Fixed {filename}")
        else:
            # Maybe the formatting is slightly different, let's use regex
            import re
            content = re.sub(
                r"const closeSign = h\.avg_close_gain >= 0 \? '\+' : '';\s*tr\.innerHTML = `",
                r"const closeSign = h.avg_close_gain >= 0 ? '+' : '';\n                    const avgMax = h.avg_max_gain_pct || 0;\n                    const avgClose = h.avg_closing_gain_pct || 0;\n                    tr.innerHTML = `",
                content
            )
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Fixed {filename} via regex")
    except Exception as e:
        print(e)

