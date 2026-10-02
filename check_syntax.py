with open("ui/app.js", "r", encoding="utf-8") as f:
    text = f.read()

import re
matches = re.finditer(r'Swal\.fire\(', text)
for i, match in enumerate(matches):
    start = max(0, match.start() - 50)
    end = min(len(text), match.end() + 250)
    print(f"--- MATCH {i} ---")
    print(text[start:end].encode('ascii', 'ignore').decode('ascii'))
