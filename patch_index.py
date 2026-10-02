with open("ui/index.html", "r", encoding="utf-8") as f:
    text = f.read()

text = text.replace("</head>", "    <!-- SweetAlert2 for Modern Modals -->\n    <script src=\"https://cdn.jsdelivr.net/npm/sweetalert2@11\"></script>\n</head>")

with open("ui/index.html", "w", encoding="utf-8") as f:
    f.write(text)
print("INDEX PATCHED")
