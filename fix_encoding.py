import os

with open("ui/index.html", "r", encoding="utf-8") as f:
    html = f.read()
html = html.replace("style.css?v=20260923_v8_allstocks_fixed", "style.css?v=20261001_final_clean")
html = html.replace("app.js?v=20260929_v11_fix_vol_sign", "app.js?v=20261001_final_clean")
with open("ui/index.html", "w", encoding="utf-8") as f:
    f.write(html)

css_additions = """
/* =========================================================
   LIGHT THEME MODERNIZATION (Colorful Headers Edition)
   ========================================================= */

body.light-mode {
    --bg-base: #F6F8FB !important;
    --bg-card: #FFFFFF !important;
    --bg-card-hover: #F8FAFC !important;
    --border-color: #E5E7EB !important;
    --text-main: #111827 !important;
    --text-muted: #667085 !important;
    --accent-blue: #2563EB !important;
    --accent-green: #16A34A !important;
    --accent-red: #DC2626 !important;
    --accent-yellow: #D97706 !important;
    --card-bg: #FFFFFF !important;
}

body.light-mode .card, 
body.light-mode .summary-card, 
body.light-mode .glass-panel {
    background: #FFFFFF !important;
    border: 1px solid #E5E7EB !important;
    box-shadow: 0 4px 6px -1px rgba(17, 24, 39, 0.05), 0 2px 4px -1px rgba(17, 24, 39, 0.03) !important;
    border-radius: 12px !important;
}

body.light-mode .top-nav {
    background: #FFFFFF !important;
    border-bottom: 1px solid #E5E7EB !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.02) !important;
}

body.light-mode .nav-btn {
    background: transparent !important;
    color: #475569 !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 500 !important;
    padding: 6px 14px !important;
    margin: 2px 4px !important;
}

body.light-mode .nav-btn:hover {
    background: #F1F5F9 !important;
    color: #0F172A !important;
}

body.light-mode .nav-btn.active {
    background: #EFF6FF !important;
    color: #2563EB !important;
    font-weight: 600 !important;
}

body.light-mode #v8-wrapper h2 {
    color: #D97706 !important;
}
body.light-mode .nav-btn[href="/#v8"] {
    color: #D97706 !important;
}
body.light-mode .nav-btn[href="/#v8"].active {
    background: #FEF3C7 !important;
}

body.light-mode #live-radar-container h2 {
    color: #DC2626 !important; 
}

body.light-mode #home-top-picks h3, 
body.light-mode #portfolio-container h3,
body.light-mode .card-title i.fa-fire {
    color: #F59E0B !important; 
}

body.light-mode input[type="search"], 
body.light-mode input[type="text"] {
    background: #FFFFFF !important;
    border: 1px solid #CBD5E1 !important;
    color: #0F172A !important;
    box-shadow: 0 1px 2px rgba(0,0,0,0.05) inset !important;
}
body.light-mode input[type="search"]:focus {
    border-color: #2563EB !important;
    outline: 2px solid rgba(37, 99, 235, 0.2) !important;
}

body.light-mode button[onclick^="quickTradeBuy"] {
    border-radius: 6px !important;
    text-transform: uppercase;
    font-size: 0.72rem !important;
    padding: 4px 12px !important;
    box-shadow: 0 1px 2px rgba(0,0,0,0.05) !important;
}

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

body.light-mode [style*="rgba(0,0,0"],
body.light-mode [style*="rgba(0, 0, 0"],
body.light-mode [style*="rgba(30,41,59"],
body.light-mode [style*="rgba(15,23,42"] {
    background: transparent !important;
    background-color: transparent !important;
}

body.light-mode details.card[style*="rgba(15,23,42,0.95)"] {
    background: #FFFFFF !important;
    border: 1px solid #E2E8F0 !important;
}

body.light-mode .card[style*="linear-gradient"] {
    background: #FFFFFF !important;
    border-color: #E2E8F0 !important;
    box-shadow: 0 2px 4px rgba(0,0,0,0.05) !important;
}

body.light-mode #market-closed-warning {
    background: linear-gradient(135deg, rgba(120,53,15,0.1), rgba(245,158,11,0.1)) !important;
    color: #9A3412 !important;
    border: 1px solid rgba(245,158,11,0.4) !important;
}
body.light-mode #market-closed-warning-detail {
    color: #B45309 !important;
}
body.light-mode #market-closed-warning i {
    color: #D97706 !important;
}
"""
with open("ui/style.css", "a", encoding="utf-8") as f:
    f.write("\n" + css_additions)
print("done")
