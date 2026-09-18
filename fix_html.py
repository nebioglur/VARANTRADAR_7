with open("ui/index.html", "r", encoding="utf-8") as f:
    text = f.read()

import re
# daily button should be purple
text = text.replace(
    'id="stats-mode-daily-btn" onclick="switchStatsMode(\'daily\')" style="background:transparent; border:none; color:var(--text-muted);',
    'id="stats-mode-daily-btn" onclick="switchStatsMode(\'daily\')" style="background:var(--accent-purple); border:none; color:#fff;'
)
# cumulative button should be transparent
text = text.replace(
    'id="stats-mode-cumulative-btn" onclick="switchStatsMode(\'cumulative\')" style="background:var(--accent-purple); border:none; color:#fff;',
    'id="stats-mode-cumulative-btn" onclick="switchStatsMode(\'cumulative\')" style="background:transparent; border:none; color:var(--text-muted);'
)

with open("ui/index.html", "w", encoding="utf-8") as f:
    f.write(text)

print("HTML FIX DONE")
