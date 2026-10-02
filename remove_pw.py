import re

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Remove check_password block
pattern1 = r"def check_password\(\):.*?if not check_password\(\):\n    st\.stop\(\)\n"
content = re.sub(pattern1, "", content, flags=re.DOTALL)

# 2. Remove V7 admin password block
pattern2 = r"if 'admin_logged_in' not in st\.session_state:.*?else:\n    if st\.sidebar\.button\(\"🚪 Çıkış Yap\"\):\n        st\.session_state\.admin_logged_in = False\n        st\.rerun\(\)\n        \n    st\.sidebar\.success\(\"Yetkili Girişi Aktif\"\)\n    \n"
content = re.sub(pattern2, "", content, flags=re.DOTALL)

# 3. Dedent the remaining V7 section (which was indented by 4 spaces under the else)
# We find all lines starting with "    " after the V7 Kurumsal Yönetim header and dedent them.
# A simpler way: just split the content by lines, find the V7 section, and dedent it.
lines = content.split('\n')
new_lines = []
in_v7 = False
for line in lines:
    if "### ⚙️ V7 Kurumsal Yönetim" in line:
        in_v7 = True
        new_lines.append(line)
        continue
    
    if in_v7:
        if line.startswith("    "):
            new_lines.append(line[4:])
        else:
            new_lines.append(line)
    else:
        new_lines.append(line)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write('\n'.join(new_lines))

print("app.py successfully modified to remove all passwords.")
