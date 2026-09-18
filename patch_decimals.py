# -*- coding: utf-8 -*-
with open('ui/app.js', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace(
    "${r.cash.toLocaleString('tr-TR', {maximumFractionDigits: 0})}",
    "${r.cash.toLocaleString('tr-TR', {minimumFractionDigits: 2, maximumFractionDigits: 2})}"
)
text = text.replace(
    "${r.invested.toLocaleString('tr-TR', {maximumFractionDigits: 0})}",
    "${r.invested.toLocaleString('tr-TR', {minimumFractionDigits: 2, maximumFractionDigits: 2})}"
)

with open('ui/app.js', 'w', encoding='utf-8') as f:
    f.write(text)
print("APP.JS PATCH OK")
