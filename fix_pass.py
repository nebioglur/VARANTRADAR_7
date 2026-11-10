with open("services/market_data.py", "r", encoding="utf-8") as f:
    code = f.read()

code = code.replace("except Exception:\n                    pass", "except Exception as e:\n                    print('ERROR IN EXECUTEMANY:', e)")

with open("services/market_data.py", "w", encoding="utf-8") as f:
    f.write(code)
print("Updated market_data.py")
