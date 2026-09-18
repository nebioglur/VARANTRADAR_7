# -*- coding: utf-8 -*-
import codecs

with codecs.open('ui/style.css', 'r', 'utf-8') as f:
    text = f.read()

start_idx = text.find('/* ===== A')
end_str = 'body.light-mode .sidebar-tabs { background: rgba(241,245,249,0.6); }'
end_idx = text.find(end_str)

if start_idx != -1 and end_idx != -1:
    end_idx += len(end_str)
    
    new_theme = '''/* ===== ACIK TEMA (Light Mode) - KURUMSAL ===== */
body.light-mode {
    --bg-base: #EEF2F6;
    --bg-card: #FFFFFF;
    --bg-card-hover: #F8FAFC;
    --border-color: #E2E8F0;
    --text-main: #1E293B;
    --text-muted: #64748B;
    --accent-blue: #1D4ED8;
    --accent-blue-hover: #1E3A8A;
    --accent-green: #15803D;
    --accent-red: #B91C1C;
    --accent-yellow: #B45309;
    --accent-purple: #6D28D9;
    --shadow-sm: 0 1px 2px 0 rgba(0,0,0,0.05);
    --shadow-md: 0 4px 6px -1px rgba(0,0,0,0.05), 0 2px 4px -1px rgba(0,0,0,0.03);
    --shadow-lg: 0 10px 15px -3px rgba(0,0,0,0.05), 0 4px 6px -2px rgba(0,0,0,0.03);
}

body.light-mode { background: var(--bg-base); color: var(--text-main); }
body.light-mode .top-nav {
    background: #FFFFFF;
    border-bottom: 1px solid #E2E8F0;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}
body.light-mode .card {
    background: var(--bg-card) !important;
    border: 1px solid var(--border-color) !important;
    box-shadow: var(--shadow-sm) !important;
    color: var(--text-main);
    border-radius: 8px;
}
body.light-mode .card h3, body.light-mode .card-title {
    color: #0F172A !important;
    font-weight: 700;
}

/* Zorunlu eziyoruz, inline stiller siritiyor */
body.light-mode [style*="color:var(--text-light)"],
body.light-mode [style*="color:#fff"] {
    color: #0F172A !important;
    font-weight: 700 !important;
}
body.light-mode [style*="color:var(--accent-yellow)"] { color: #B45309 !important; }
body.light-mode [style*="color:var(--accent-green)"] { color: #15803D !important; }
body.light-mode [style*="color:var(--accent-red)"] { color: #B91C1C !important; }

/* Tablolar - Kurumsal finans havasi */
body.light-mode .data-table {
    border-collapse: separate;
    border-spacing: 0;
}
body.light-mode .data-table th { 
    background-color: #F1F5F9 !important; 
    color: #475569 !important; 
    font-weight: 700;
    text-transform: uppercase;
    font-size: 0.75rem;
    letter-spacing: 0.5px;
    border-bottom: 2px solid #E2E8F0 !important;
    border-top: 1px solid #E2E8F0 !important;
}
body.light-mode .data-table td { 
    color: #1E293B; 
    border-bottom: 1px solid #F1F5F9 !important;
}
body.light-mode .data-table tr:hover td { 
    background: #F8FAFC !important; 
}

/* Buton ve Girdiler */
body.light-mode #symbol-input { background: #FFFFFF; border-color: #CBD5E1; color: #0F172A; box-shadow: inset 0 1px 2px rgba(0,0,0,0.05); }
body.light-mode .s-tab { color: #64748B; }
body.light-mode .s-tab:hover { background: #F1F5F9; color: #0F172A; }
body.light-mode .s-tab.active { background: #EEF2FF; color: #4338CA; font-weight:600; }

body.light-mode .nav-btn { color: #64748B; border-bottom: 2px solid transparent; }
body.light-mode .nav-btn:hover { background: #F1F5F9; color: #0F172A; }
body.light-mode .nav-btn.active { color: #4338CA; background: transparent; border-bottom-color: #4338CA; font-weight:700; }

body.light-mode .bottom-mobile-bar {
    background: #FFFFFF;
    border-top: 1px solid #E2E8F0;
    box-shadow: 0 -4px 10px rgba(0,0,0,0.05);
}
body.light-mode .sidebar-tabs { background: #F8FAFC; border-right: 1px solid #E2E8F0; }

/* Rozetler ve Butonlar (AL/SAT) */
body.light-mode span[style*="background:#22c55e22"], body.light-mode span[style*="border:1px solid #22c55e66"] {
    background: #DCFCE7 !important; color: #166534 !important; border-color: #86EFAC !important;
}
body.light-mode span[style*="background:#3b82f622"], body.light-mode span[style*="border:1px solid #3b82f666"] {
    background: #DBEAFE !important; color: #1E40AF !important; border-color: #93C5FD !important;
}
body.light-mode span[style*="background:#f9731622"], body.light-mode span[style*="border:1px solid #f9731666"] {
    background: #FFEDD5 !important; color: #9A3412 !important; border-color: #FDBA74 !important;
}
body.light-mode span[style*="background:#ef444422"], body.light-mode span[style*="border:1px solid #ef444466"] {
    background: #FEE2E2 !important; color: #991B1B !important; border-color: #FCA5A5 !important;
}

body.light-mode button[style*="rgba(34,197,94,0.2)"] {
    background: #DCFCE7 !important; color: #166534 !important; border-color: #86EFAC !important;
}
body.light-mode button[style*="rgba(239,68,68,0.2)"] {
    background: #FEE2E2 !important; color: #991B1B !important; border-color: #FCA5A5 !important;
}'''

    text = text[:start_idx] + new_theme + text[end_idx:]
    with codecs.open('ui/style.css', 'w', 'utf-8') as f:
        f.write(text)
    print("THEME PATCHED")
else:
    print("THEME BLOCK NOT FOUND")
