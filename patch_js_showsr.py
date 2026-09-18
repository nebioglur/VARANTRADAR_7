# -*- coding: utf-8 -*-
with open('ui/app.js', 'r', encoding='utf-8') as f:
    text = f.read()

old_func = '''function showSR(sym, price, high, low) {
    let p_val = (high + low + price) / 3;'''

new_func = '''window.showSR = function(sym, price, high, low) {
    try {
        price = parseFloat(price) || 0;
        high = parseFloat(high) || price;
        low = parseFloat(low) || price;
        let p_val = (high + low + price) / 3;'''

if old_func in text:
    text = text.replace(old_func, new_func)
    # Also replace function showSR(sym, price, high, low) { if it's there
else:
    print("Function not found exactly.")

with open('ui/app.js', 'w', encoding='utf-8') as f:
    f.write(text)

print("SHOWSR PATCH OK")
