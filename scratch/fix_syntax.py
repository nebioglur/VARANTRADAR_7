with open('server.py', 'r', encoding='utf-8') as f:
    content = f.read()

import re
content = re.sub(r'x\[\\\'score\\\'\]', 'x["score"]', content)
content = re.sub(r'x\[\\\\\'score\\\\\'\]', 'x["score"]', content)
content = content.replace("x[\'score\']", 'x["score"]')

with open('server.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("Done")
