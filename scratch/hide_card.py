with open('ui/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

import re
content = re.sub(r'<div class="card" style="background: linear-gradient\(145deg, rgba\(168,85,247,0\.05\) 0%, rgba\(15,23,42,1\) 100%\); border:1px solid rgba\(168,85,247,0\.2\); text-align:center; padding: 1\.5rem;">', 
                 '<div class="card" style="display:none; background: linear-gradient(145deg, rgba(168,85,247,0.05) 0%, rgba(15,23,42,1) 100%); border:1px solid rgba(168,85,247,0.2); text-align:center; padding: 1.5rem;">', 
                 content)

with open('ui/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("Done")
