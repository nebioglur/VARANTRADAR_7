with open('ui/app.js', 'r', encoding='utf-8') as f:
    text = f.read()

bad = '    return `<span style="${color}\n\nfunction translateV8Reason'
good = '    return `<span style="${color}">${current.toFixed(2)} (${sign}${chg.toFixed(2)}%)</span>`;\n}\n\nfunction translateV8Reason'

if bad in text:
    text = text.replace(bad, good)
    with open('ui/app.js', 'w', encoding='utf-8') as f:
        f.write(text)
    print("Properly restored formatV8Price!")
else:
    print("Could not find bad string!")
