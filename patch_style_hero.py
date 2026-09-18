# -*- coding: utf-8 -*-
with open('ui/style.css', 'a', encoding='utf-8') as f:
    f.write('''
/* --- ACIK TEMA: HERO BANNER & SLIDER & FILTERS --- */
body.light-mode .glass-panel[style*="linear-gradient(145deg, rgba(30,30,35,0.9)"] {
    background: linear-gradient(135deg, #1E3A8A, #1D4ED8) !important;
    border: none !important;
    color: #FFFFFF !important;
    box-shadow: 0 10px 25px -5px rgba(29, 78, 216, 0.4) !important;
}
body.light-mode .glass-panel[style*="linear-gradient"] [style*="color:var(--text-muted)"] {
    color: #93C5FD !important;
}
body.light-mode .glass-panel[style*="linear-gradient"] [style*="color:var(--text-main)"] {
    color: #FFFFFF !important;
}
body.light-mode .glass-panel[style*="linear-gradient"] [style*="background:var(--bg-secondary)"] {
    background: rgba(255, 255, 255, 0.1) !important;
    border: 1px solid rgba(255, 255, 255, 0.2) !important;
}
body.light-mode #live-clock {
    background: none !important;
    -webkit-text-fill-color: #FFFFFF !important;
    text-shadow: 0 2px 4px rgba(0,0,0,0.3) !important;
}

body.light-mode .mobile-slider-controls {
    background: #FFFFFF !important;
    border: 1px solid #E2E8F0 !important;
    box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05) !important;
}
body.light-mode .slider-nav-btn {
    background: #F8FAFC !important;
    color: #0F172A !important;
    border: 1px solid #CBD5E1 !important;
}
body.light-mode .slider-nav-btn:hover {
    background: #E2E8F0 !important;
}
body.light-mode .indicator-dot {
    background: #F8FAFC !important;
    color: #475569 !important;
    border: 1px solid #E2E8F0 !important;
}
body.light-mode .indicator-dot.active {
    background: #2563EB !important;
    color: #FFFFFF !important;
    border-color: #2563EB !important;
}
body.light-mode .indicator-dot[style*="color:#0ea5e9"] {
    color: #0284C7 !important;
}
body.light-mode .indicator-dot.active[style*="color:#0ea5e9"] {
    color: #FFFFFF !important;
}

body.light-mode .filter-btn {
    background: #FFFFFF !important;
    color: #475569 !important;
    border: 1px solid #CBD5E1 !important;
    box-shadow: 0 1px 2px rgba(0,0,0,0.05) !important;
}
body.light-mode .filter-btn:hover {
    background: #F8FAFC !important;
    color: #0F172A !important;
}
body.light-mode .filter-btn.active {
    background: #2563EB !important;
    color: #FFFFFF !important;
    border-color: #2563EB !important;
}

body.light-mode #total-analyzed-counter {
    background: #DCFCE7 !important;
    color: #166534 !important;
    border-color: #86EFAC !important;
    box-shadow: 0 2px 4px rgba(22, 101, 52, 0.1) !important;
}
''')
