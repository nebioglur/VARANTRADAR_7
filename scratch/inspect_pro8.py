with open('pro8_app.js', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

print("File length:", len(text))
lines = text.splitlines()
print("Total lines:", len(lines))
print("\nFirst 20 lines:")
for l in lines[:20]:
    print(l)

print("\nLast 30 lines:")
for l in lines[-30:]:
    print(l)
