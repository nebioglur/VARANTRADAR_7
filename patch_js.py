# -*- coding: utf-8 -*-
with open('live_app.js', 'r', encoding='utf-8') as f:
    content = f.read()

func_str = '''
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
    
    // Sort by change % descending
    allStats.sort((a, b) => b.change - a.change);
    
    tbody.innerHTML = allStats.map(s => {
        const color = s.change > 0 ? 'var(--accent-green)' : (s.change < 0 ? 'var(--accent-red)' : 'var(--text-color)');
        return \
            <tr>
                <td style="font-weight:bold;">\</td>
                <td>₺\</td>
                <td style="color:\; font-weight:bold;">\\%</td>
                <td>\M</td>
                <td style="color:var(--text-muted);">\</td>
            </tr>
        \;
    }).join('');
}
'''

# Find renderAllDashboardTables and inject our call
old_render = '''function renderAllDashboardTables() {
    if (!window.dashboardData) return;'''
new_render = '''function renderAllDashboardTables() {
    if (!window.dashboardData) return;
    renderAllStocksTable();'''

content = content + "\n" + func_str
content = content.replace(old_render, new_render)

with open('live_app.js', 'w', encoding='utf-8') as f:
    f.write(content)

print("JS YAZILDI")
