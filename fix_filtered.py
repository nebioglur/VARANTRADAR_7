# -*- coding: utf-8 -*-
with open("services/tavan_tracker.py", "r", encoding="utf-8") as f:
    code = f.read()

bad = """            filtered.append(item)

        if not filtered:
            return {}

        now = datetime.now()"""
good = """            filtered.append(item)

        now = datetime.now()"""
code = code.replace(bad, good)

with open("services/tavan_tracker.py", "w", encoding="utf-8") as f:
    f.write(code)
print("Removed if not filtered check!")
