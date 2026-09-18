with open("services/notification_manager.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if "DA" in line and "KEKL" in line and "TAVAN RADARI" in line:
        line = line.replace("DA", "").replace("KEKL", "").replace("  ", " ").replace("TAVAN RADARI", "VIP TAVAN RADARI")
        # Just hardcode a clean version
        line = '        msg = f"\U0001F680 <b>[{phase}] VIP TAVAN RADARI</b> \U0001F680\\n\\n"\n'
    new_lines.append(line)

text = "".join(new_lines)
import re
pattern = r'(phase = extra\.get\("Phase_Badge", "TAVAN RADARI"\))'
replacement = r'\1\n        if phase and "Erken" in phase:\n            return True\n'
text = re.sub(pattern, replacement, text)

with open("services/notification_manager.py", "w", encoding="utf-8") as f:
    f.write(text)
print("NOTIF PATCH 3 OK")
