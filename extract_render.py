with open("ui/app.js", "r", encoding="utf-8") as f:
    text = f.read()

start = text.find("function renderStatsMode()")
end = text.find("function renderStatsHistoryTable", start)
print(text[start:end])
