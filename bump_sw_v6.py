with open("ui/sw.js", "r", encoding="utf-8") as f:
    code = f.read()
code = code.replace("vr-static-v5", "vr-static-v6")
with open("ui/sw.js", "w", encoding="utf-8") as f:
    f.write(code)

with open("ui/index.html", "r", encoding="utf-8") as f:
    idx = f.read()
idx = idx.replace("app.js?v=5", "app.js?v=6")
idx = idx.replace("style.css?v=5", "style.css?v=6")
with open("ui/index.html", "w", encoding="utf-8") as f:
    f.write(idx)
print("Bumped to v6")
