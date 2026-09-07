add = """
/* PIYASA DEDEKTIFI */
.dt-filter { background: transparent; border: 1px solid var(--border-color); color: var(--text-muted); border-radius: 20px; padding: 0.3rem 0.85rem; font-size: 0.75rem; font-weight: 700; cursor: pointer; transition: all .15s; }
.dt-filter:hover { color: #f97316; border-color: #f9731666; }
.dt-filter.active { background: #f97316; color: #fff; border-color: #f97316; }
"""
s = open('ui/style.css', encoding='utf-8').read()
if 'PIYASA DEDEKTIFI' not in s:
    open('ui/style.css', 'w', encoding='utf-8').write(s + add)
    print('CSS OK (eklendi)')
else:
    print('CSS zaten var')
