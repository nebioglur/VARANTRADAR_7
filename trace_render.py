with open("ui/app.js", "r", encoding="utf-8") as f:
    text = f.read()

start = text.find("} else {", text.find("if (current_stats_mode === 'cumulative') {"))
end = text.find("if (el('stats-tab-total-days'))", start)
print(text[start:end])
