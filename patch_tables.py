# -*- coding: utf-8 -*-
with open('ui/style.css', 'r', encoding='utf-8') as f:
    text = f.read()

# I will append modern table styling at the end, which will override previous ones
modern_table_css = """
/* =========================================================
   ULTRA MODERN CORPORATE TABLE REDESIGN
   ========================================================= */
.data-table {
    border-collapse: separate !important;
    border-spacing: 0 !important;
    border-radius: 8px !important;
    overflow: hidden !important;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06) !important;
    border: 1px solid var(--border-color) !important;
}

.data-table thead th {
    background: rgba(0,0,0,0.15) !important;
    color: var(--text-muted) !important;
    font-weight: 700 !important;
    font-size: 0.75rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.5px !important;
    padding: 12px 16px !important;
    border-bottom: 2px solid var(--border-color) !important;
    text-align: left !important;
}

.data-table tbody td {
    padding: 12px 16px !important;
    font-size: 0.85rem !important;
    font-weight: 500 !important;
    border-bottom: 1px solid var(--border-color) !important;
    vertical-align: middle !important;
}

.data-table tbody tr:last-child td {
    border-bottom: none !important;
}

.data-table tbody tr:hover td {
    background-color: rgba(59, 130, 246, 0.08) !important;
    transition: background-color 0.2s ease !important;
}

/* Light Mode Corporate Professional Overrides */
body.light-mode .data-table {
    background-color: #ffffff !important;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03) !important;
    border: 1px solid #e2e8f0 !important;
}

body.light-mode .data-table thead th {
    background: #f8fafc !important;
    color: #475569 !important;
    border-bottom: 2px solid #cbd5e1 !important;
}

body.light-mode .data-table tbody td {
    border-bottom: 1px solid #f1f5f9 !important;
    color: #1e293b !important;
}

body.light-mode .data-table tbody tr:nth-child(even) td {
    background-color: #f8fafc !important;
}

body.light-mode .data-table tbody tr:hover td {
    background-color: #f1f5f9 !important;
}
"""

with open('ui/style.css', 'a', encoding='utf-8') as f:
    f.write(modern_table_css)
print("TABLE CSS PATCH OK")
