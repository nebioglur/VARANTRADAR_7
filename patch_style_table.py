# -*- coding: utf-8 -*-
with open('ui/style.css', 'a', encoding='utf-8') as f:
    f.write('''
/* --- ACIK TEMA: TABLOLARDAKI (HISSELER) INLINE SIYAH ARKA PLANLARI EZME --- */
body.light-mode .data-table tr, 
body.light-mode .data-table td,
body.light-mode table tr,
body.light-mode table td {
    background: transparent !important;
    background-color: transparent !important;
}

body.light-mode table tbody tr:nth-child(odd) {
    background-color: #FFFFFF !important;
}
body.light-mode table tbody tr:nth-child(even) {
    background-color: #F8FAFC !important;
}
body.light-mode table tbody tr:hover td,
body.light-mode table tbody tr:hover {
    background-color: #F1F5F9 !important;
}

/* Javascript tarafindan basilan kapkaranlik inline background lari temizle */
body.light-mode [style*="rgba(0,0,0"],
body.light-mode [style*="rgba(0, 0, 0"],
body.light-mode [style*="rgba(30,41,59"],
body.light-mode [style*="rgba(15,23,42"] {
    background: transparent !important;
    background-color: transparent !important;
}

body.light-mode tr[style*="rgba(0,0,0"],
body.light-mode td[style*="rgba(0,0,0"] {
    background-color: #FFFFFF !important;
}

body.light-mode .scenario-box,
body.light-mode .cio-verdict-box {
    background-color: #F8FAFC !important;
    border-color: #E2E8F0 !important;
    color: #1E293B !important;
}
''')
