with open('ui/app.js', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find('function refreshV8Data')
if idx != -1:
    print("Found refreshV8Data:")
    print(text[idx:idx+1500])
else:
    idx2 = text.find('refreshV8Data =')
    print("refreshV8Data = at:", idx2)
    if idx2 != -1:
        print(text[idx2:idx2+1500])
