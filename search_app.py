import os
def search_in_file(path, words):
    with open(path, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f.readlines()):
            for word in words:
                if word in line.lower():
                    print(f"{i+1}: {line.strip()}")
                    break

search_in_file(r"C:\Users\nebio\Desktop\VarantRadarPro\ui\app.js", ["fetch", "ai", "feedback", "ask", "gemini"])
