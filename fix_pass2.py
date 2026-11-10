with open("services/market_data.py", "r", encoding="utf-8") as f:
    code = f.read()

code = code.replace("if all_rows:", "print('ALL_ROWS LEN:', len(all_rows))\n            if all_rows:")

with open("services/market_data.py", "w", encoding="utf-8") as f:
    f.write(code)
print("Updated market_data.py")
