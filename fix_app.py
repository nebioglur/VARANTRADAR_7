# -*- coding: utf-8 -*-
with open("ui/app.js", "r", encoding="utf-8") as f:
    text = f.read()

# 1. Inject global alert override at the top
override = """
// --- Modern UI Overrides ---
window.alert = function(message) {
    if (typeof Swal !== 'undefined') {
        Swal.fire({
            title: 'Sistem Mesaji',
            text: message,
            icon: 'info',
            background: '#1a1f2e',
            color: '#fff',
            confirmButtonColor: '#38bdf8'
        });
    } else {
        console.log("Alert:", message);
    }
};

window.modernConfirm = async function(message) {
    if (typeof Swal !== 'undefined') {
        const res = await Swal.fire({
            title: 'Onay',
            text: message,
            icon: 'warning',
            showCancelButton: true,
            background: '#1a1f2e',
            color: '#fff',
            confirmButtonText: 'Evet',
            cancelButtonText: 'Iptal',
            confirmButtonColor: '#10b981',
            cancelButtonColor: '#ef4444'
        });
        return res.isConfirmed;
    }
    return true; // Fallback
};

"""
text = override + text

# 2. Replace the exact confirm usages
text = text.replace("!confirm('Bu pozisyonu", "!(await window.modernConfirm('Bu pozisyonu")
text = text.replace("!confirm('Portf", "!(await window.modernConfirm('Portf")
text = text.replace("!confirm(action === 'approve'", "!(await window.modernConfirm(action === 'approve'")
text = text.replace("!confirm(`Emin misiniz?", "!(await window.modernConfirm(`Emin misiniz?")

with open("ui/app.js", "w", encoding="utf-8") as f:
    f.write(text)

print("FIX DONE")
