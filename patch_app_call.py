# -*- coding: utf-8 -*-
with open('ui/app.js', 'r', encoding='utf-8') as f:
    text = f.read()

target = '''function renderAllDashboardTables() {
    renderAllStocksTable();'''
    
replacement = '''function renderAllDashboardTables() {
    renderAllStocksTable();
    if (typeof renderSuper12Table === 'function') renderSuper12Table();'''

if target in text:
    text = text.replace(target, replacement)
    with open('ui/app.js', 'w', encoding='utf-8') as f:
        f.write(text)
    print("CALL PATCH OK")
else:
    print("CALL PATCH NOT FOUND")
