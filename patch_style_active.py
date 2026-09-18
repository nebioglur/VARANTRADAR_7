# -*- coding: utf-8 -*-
with open('ui/style.css', 'a', encoding='utf-8') as f:
    f.write('''
/* Aktif Pill Butonlari */
body.light-mode .pill-btn.active {
    background: #2563EB !important;
    color: #FFFFFF !important;
    border-color: #2563EB !important;
}
/* Detaylar Karti */
body.light-mode details.card {
    background: #FFFFFF !important;
    border: 1px solid #E2E8F0 !important;
    box-shadow: 0 2px 4px rgba(0,0,0,0.05) !important;
}
body.light-mode details.card[style*="rgba(15,23,42,0.95)"] {
    background: #FFFFFF !important;
    border: 1px solid #E2E8F0 !important;
}
/* Ekstra siyah buton (Sabah Adaylari vb) */
body.light-mode button[style*="rgba(239,68,68,0.25)"] {
    background: #FEE2E2 !important;
    color: #991B1B !important;
    border-color: #FCA5A5 !important;
}
''')
