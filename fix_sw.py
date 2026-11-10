with open("ui/sw.js", "r", encoding="utf-8") as f:
    sw = f.read()
sw = sw.replace("vr-static-v3", "vr-static-v4")
with open("ui/sw.js", "w", encoding="utf-8") as f:
    f.write(sw)

with open("ui/index.html", "r", encoding="utf-8") as f:
    idx = f.read()
idx = idx.replace("app.js?v=20261001_final_clean_v3", "app.js?v=20261001_final_clean_v4")
idx = idx.replace("style.css?v=20261001_final_clean", "style.css?v=20261001_final_clean_v4")
with open("ui/index.html", "w", encoding="utf-8") as f:
    f.write(idx)
print("BUMPED v4")
