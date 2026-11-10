import re

with open(r'c:\Users\nebioglur\Desktop\TUM MASAUSTU_Kurtarilan\TUM MASAUSTU\VarantRadarPro\ui\app.js', 'r', encoding='utf-8') as f:
    content = f.read()

# Check line endings
has_crlf = '\r\n' in content
has_lf = '\n' in content and not has_crlf
print(f"Line endings: CRLF={has_crlf}, LF-only={has_lf}")

# Find the exact text around line 4718
lines = content.split('\n')
print(f"\nTotal lines: {len(lines)}")

# Find "Render Equity Curve Chart" line
for i, line in enumerate(lines):
    if 'Render Equity Curve Chart' in line:
        print(f"\nFound chart render at line {i+1}")
        # Show context
        for j in range(max(0,i-2), min(len(lines), i+8)):
            print(f"  L{j+1}: {repr(lines[j])}")
        break

# Find "Render Trades Table" line
for i, line in enumerate(lines):
    if 'Render Trades Table' in line:
        print(f"\nFound trades table at line {i+1}")
        for j in range(max(0,i-2), min(len(lines), i+4)):
            print(f"  L{j+1}: {repr(lines[j])}")
        break

# Find the closing of tbody block -> "} else {"
for i, line in enumerate(lines):
    if i > 4750 and '        } else {' in line and i < 4800:
        print(f"\nFound else block at line {i+1}")
        for j in range(max(0,i-3), min(len(lines), i+5)):
            print(f"  L{j+1}: {repr(lines[j])}")
        break
