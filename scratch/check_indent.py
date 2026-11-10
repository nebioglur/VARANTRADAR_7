with open('main.py', 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

# Line 137 was: '        if df is None or df.empty:\n'
# It has 8 spaces. Lines 138-171 had 8 spaces (same level instead of 12 spaces).
# Or line 137 can have 4 spaces '    if df is None or df.empty:\n' and lines 138-171 have 8 spaces!
# Let's check lines 130-140 context:

# Look at lines before 137:
# 134: '        except Exception:\n'
# 135: '            pass\n'
# 136: '\n'
# 137: '        if df is None or df.empty:\n' -> this should be 4 spaces! '    if df is None or df.empty:\n'
# and lines 138-171 already have 8/12 spaces.
# Let's inspect indentation from line 132 to 175:

for i in range(130, 145):
    print(i+1, repr(lines[i]))

