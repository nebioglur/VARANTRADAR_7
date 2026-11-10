import re

with open('ui/app.js', 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Update _ltQuotePrice
old_func = '''function _ltQuotePrice() {
    const q = document.getElementById('lq-price');
    if (!q) return null;
    const v = parseFloat((q.textContent || '').replace(/[^\d.,]/g, '').replace(',', '.'));
    return (v && v > 0) ? v : null;
}'''

new_func = '''function _ltQuotePrice() {
    const inputEl = document.getElementById('lt-price');
    if (inputEl && inputEl.value) {
        const v = parseFloat(inputEl.value.replace(',', '.'));
        if (v > 0) return v;
    }
    const q = document.getElementById('lq-price');
    if (!q) return null;
    const v = parseFloat((q.textContent || '').replace(/[^\d.,]/g, '').replace(',', '.'));
    return (v && v > 0) ? v : null;
}'''

if old_func in text:
    text = text.replace(old_func, new_func)

# 2. Update lt-price event listener
old_listener = '''        if (qty > 0 && p > 0) {
            const allocInput = document.getElementById('lt-allocation');
            if (allocInput) allocInput.value = Math.round(qty * p * 100) / 100;
        }
        
        ltUpdateQty();
        _ltSyncing = false;
    });'''

new_listener = '''        if (qty > 0 && p > 0) {
            const allocInput = document.getElementById('lt-allocation');
            if (allocInput) allocInput.value = Math.round(qty * p * 100) / 100;
        }
        
        ltUpdateQty();
        
        // TP ve SL'yi yeni fiyata gore guncelle
        ltSyncFromPct('tp');
        ltSyncFromPct('sl');
        
        _ltSyncing = false;
    });'''

if old_listener in text:
    text = text.replace(old_listener, new_listener)

with open('ui/app.js', 'w', encoding='utf-8') as f:
    f.write(text)
print('Patched app.js')
