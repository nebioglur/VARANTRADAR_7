import os

css = """
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
    --card-bg: #FFFFFF !important; /* Mobile scroll fix */
}

/* Base structural overrides */
body.light-mode .card, 
body.light-mode .summary-card, 
body.light-mode .glass-panel {
    background: #FFFFFF !important;
    border: 1px solid #E5E7EB !important;
    box-shadow: 0 4px 6px -1px rgba(17, 24, 39, 0.05), 0 2px 4px -1px rgba(17, 24, 39, 0.03) !important;
    border-radius: 12px !important;
}

/* TURN DARK INLINE BACKGROUNDS INTO LIGHT GREY FOR LIGHT MODE */
body.light-mode [style*="rgba(15,23,42,1)"],
body.light-mode [style*="rgba(15, 23, 42, 1)"],
body.light-mode [style*="rgba(15,23,42,0.95)"],
body.light-mode [style*="rgba(30,41,59,0.8)"] {
    background: #F8FAFC !important;
    color: #0F172A !important;
    border: 1px solid #E2E8F0 !important;
}

/* If a table header was turned light grey, ensure its text is dark */
body.light-mode [style*="rgba(15,23,42,1)"] *,
body.light-mode [style*="rgba(15, 23, 42, 1)"] * {
    color: #0F172A !important;
}

/* EXCEPTIONS: Warning boxes */
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
    f.write("\n" + css)
