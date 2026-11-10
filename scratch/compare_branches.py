import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('ui/app.js', 'r', encoding='utf-8', errors='ignore') as f:
    main_lines = f.readlines()

with open('pro8_app.js', 'r', encoding='utf-8', errors='ignore') as f:
    pro8_lines = f.readlines()

import subprocess
branch_app = subprocess.check_output(['git', 'show', 'remotes/origin/fix/pro8-dip-kirilim-detective:ui/app.js'], encoding='utf-8', errors='ignore').splitlines(True)

print(f"main ui/app.js lines: {len(main_lines)}")
print(f"pro8 branch ui/app.js lines: {len(branch_app)}")
print(f"downloaded pro8_app.js lines: {len(pro8_lines)}")

# Let's check the end of pro8_app.js vs branch_app
print("\n--- Last 20 lines of pro8 branch ui/app.js ---")
for l in branch_app[-20:]:
    print(l, end='')

print("\n--- Last 20 lines of downloaded pro8_app.js ---")
for l in pro8_lines[-20:]:
    print(l, end='')
