with open("ui/sw.js", "r", encoding="utf-8") as f:
    code = f.read()

code = code.replace("const CACHE = 'vr-static-v4';", "const CACHE = 'vr-static-v5';")

with open("ui/sw.js", "w", encoding="utf-8") as f:
    f.write(code)

with open("ui/index.html", "r", encoding="utf-8") as f:
    idx = f.read()
idx = idx.replace("app.js?v=4", "app.js?v=5")
idx = idx.replace("style.css?v=4", "style.css?v=5")

with open("ui/index.html", "w", encoding="utf-8") as f:
    f.write(idx)

print("Bumped cache version to v5")
