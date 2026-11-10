with open("ui/app.js", "rb") as f:
    text = f.read().decode("utf-8", errors="ignore")
idx = 248776
start = max(0, idx - 11000)
end = idx - 9500
print(text[start:end].encode("ascii", "backslashreplace").decode("ascii"))
