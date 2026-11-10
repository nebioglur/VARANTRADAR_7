with open("ui/sw.js", "r", encoding="utf-8") as f:
    code = f.read()
code = code.replace("vr-static-v6", "vr-static-v7")
with open("ui/sw.js", "w", encoding="utf-8") as f:
    f.write(code)

with open("ui/index.html", "r", encoding="utf-8") as f:
    idx = f.read()
idx = idx.replace("app.js?v=6", "app.js?v=7")
idx = idx.replace("style.css?v=6", "style.css?v=7")
with open("ui/index.html", "w", encoding="utf-8") as f:
    f.write(idx)
print("Bumped to v7")
