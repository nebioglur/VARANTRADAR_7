# -*- coding: utf-8 -*-
with open('live_app.js', 'r', encoding='utf-8') as f:
    lines = f.readlines()

start_idx = -1
for i, line in enumerate(lines):
    if "function renderAllStocksTable()" in line:
        start_idx = i
        break

new_js = '''
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
'''

if start_idx != -1:
    del lines[start_idx:]
    lines.append(new_js)
    with open('live_app.js', 'w', encoding='utf-8') as f:
        f.writelines(lines)
    print("JS4_YAZILDI")
else:
    print("BULUNAMADI")
