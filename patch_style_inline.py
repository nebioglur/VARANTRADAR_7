# -*- coding: utf-8 -*-
with open('ui/style.css', 'a', encoding='utf-8') as f:
    f.write('''
/* --- ACIK TEMA: INLINE KOYU RENKLERI TAMAMEN EZME --- */
body.light-mode [style*="rgba(15,23,42,1)"],
body.light-mode [style*="rgba(15, 23, 42, 1)"],
body.light-mode [style*="rgba(15,23,42,0.95)"],
body.light-mode [style*="rgba(30,41,59,0.8)"],
body.light-mode [style*="background:rgba(0,0,0,0.2)"],
body.light-mode [style*="background:rgba(0,0,0,0.3)"],
body.light-mode [style*="background:rgba(255,255,255,0.03)"],
body.light-mode [style*="background:rgba(255,255,255,0.04)"],
body.light-mode [style*="background:var(--bg-secondary)"] {
    background: #FFFFFF !important;
}

/* Radar Kartlarindaki Gradient (Linear) Koyu Renkleri Ezme */
body.light-mode .card[style*="linear-gradient"] {
    background: #FFFFFF !important;
    border-color: #E2E8F0 !important;
    box-shadow: 0 2px 4px rgba(0,0,0,0.05) !important;
}

/* Pill Butonlar (Tum, Tavan Radari vb.) */
body.light-mode .pill-btn {
    background: #F8FAFC !important;
    color: #475569 !important;
    border: 1px solid #CBD5E1 !important;
}
body.light-mode .pill-btn:hover {
    background: #E2E8F0 !important;
    color: #0F172A !important;
}

body.light-mode .dip-filter-btn {
    background: #F8FAFC !important;
    color: #475569 !important;
    border: 1px solid #CBD5E1 !important;
}
body.light-mode .dip-filter-btn.active {
    background: #DCFCE7 !important;
    color: #166534 !important;
    border-color: #86EFAC !important;
}
''')
