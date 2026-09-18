# -*- coding: utf-8 -*-
with open('ui/app.js', 'r', encoding='utf-8') as f:
    appjs = f.read()

import re

# Piyasade dedektifinden sonraki cift kopyayi tespit et ve tek bir taneye dusur
dup_block = r'''// ========== /PÝYASA DEDEKTÝFÝ ==========


let currentStocksSort = { col: 'change', asc: false };

function sortAllStocks(col) {
    if (currentStocksSort.col === col) {
        currentStocksSort.asc = !currentStocksSort.asc;
    } else {
        currentStocksSort.col = col;
        currentStocksSort.asc = (col === 'symbol');
    }
    renderAllStocksTable();
}
// ========== /PÝYASA DEDEKTÝFÝ ==========


let currentStocksSort = { col: 'change', asc: false };

function sortAllStocks(col) {
    if (currentStocksSort.col === col) {
        currentStocksSort.asc = !currentStocksSort.asc;
    } else {
        currentStocksSort.col = col;
        currentStocksSort.asc = (col === 'symbol');
    }
    renderAllStocksTable();
}'''

single_block = r'''// ========== /PÝYASA DEDEKTÝFÝ ==========


let currentStocksSort = { col: 'change', asc: false };

function sortAllStocks(col) {
    if (currentStocksSort.col === col) {
        currentStocksSort.asc = !currentStocksSort.asc;
    } else {
        currentStocksSort.col = col;
        currentStocksSort.asc = (col === 'symbol');
    }
    renderAllStocksTable();
}'''

appjs = appjs.replace(dup_block, single_block)

with open('ui/app.js', 'w', encoding='utf-8') as f:
    f.write(appjs)
print("DUP_FIXED")
