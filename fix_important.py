with open("ui/style.css", "r", encoding="utf-8") as f:
    css = f.read()

# Replace color: #1e293b !important; with color: #1e293b;
css = css.replace("color: #1e293b !important;", "/* color: #1e293b; removed to allow inline */")

with open("ui/style.css", "w", encoding="utf-8") as f:
    f.write(css)
print("FIXED")
