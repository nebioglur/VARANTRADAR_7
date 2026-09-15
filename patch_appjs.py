# -*- coding: utf-8 -*-
with open('ui/app.js', 'r', encoding='utf-8') as f:
    content = f.read()

func_str = """
function renderAllStocksTable() {
    const tbody = document.getElementById('tb-all-stocks-home');
    if (!tbody || !window.dashboardData || !window.dashboardData.all_symbols_stats) return;
    
    let allStats = Object.entries(window.dashboardData.all_symbols_stats).map(([sym, data]) => ({
        symbol: sym,
        price: data.Price || data.Daily_Close || 0,
        change: data.Change_Pct || 0,
        volume: data.Volume || 0,
        time: data.Time || '-'
    }));
    
    allStats.sort((a, b) => b.change - a.change);
    
    tbody.innerHTML = allStats.map(s => {
        const color = s.change > 0 ? 'var(--accent-green)' : (s.change < 0 ? 'var(--accent-red)' : 'var(--text-color)');
        const sign = s.change > 0 ? '+' : '';
        const volM = (s.volume / 1000000).toFixed(1);
        const sym = s.symbol.replace('.IS', '');
        return `
            <tr>
                <td style="font-weight:bold;">${sym}</td>
                <td>TL ${s.price.toFixed(2)}</td>
                <td style="color:${color}; font-weight:bold;">${sign}${s.change.toFixed(2)}%</td>
                <td>${volM}M</td>
                <td style="color:var(--text-muted);">${s.time}</td>
            </tr>
        `;
    }).join('');
}
"""

if "renderAllStocksTable" not in content:
    content = content + "\n" + func_str
    import re
    old_render = r"function renderAllDashboardTables\(\) {\s*const cats ="
    new_render = r"function renderAllDashboardTables() {\n    renderAllStocksTable();\n    const cats ="
    content = re.sub(old_render, new_render, content)
    
    with open('ui/app.js', 'w', encoding='utf-8') as f:
        f.write(content)
    print("APP_JS_YAMALANDI")
else:
    print("ZATEN_VAR")
