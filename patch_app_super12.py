# -*- coding: utf-8 -*-
with open('ui/app.js', 'r', encoding='utf-8') as f:
    text = f.read()

# 1. switchMainTab guncellemesi
old_switch = '''    const guideWrapper = document.getElementById('guide-wrapper');
    if (guideWrapper) guideWrapper.style.display = tabName === 'guide' ? 'block' : 'none';'''

new_switch = '''    const guideWrapper = document.getElementById('guide-wrapper');
    if (guideWrapper) guideWrapper.style.display = tabName === 'guide' ? 'block' : 'none';
    
    const super12Wrapper = document.getElementById('super12-wrapper');
    if (super12Wrapper) super12Wrapper.style.display = tabName === 'super12' ? 'block' : 'none';'''

text = text.replace(old_switch, new_switch)

# 2. renderAllStocksTable cagrilarina renderSuper12Table eklemek
# 	body.innerHTML = allStats.map(s => { ile baslayan kismi arayip fonksiyonun bitisini bulalim
# Ya da en son function renderAllStocksTable() {} bitimine ekleme yapalim.
# text icinde }).join('');\n} satirini bulup, }).join('');\n    renderSuper12Table();\n} yapabiliriz.

if "}).join('');\n}" in text:
    text = text.replace("}).join('');\n}", "}).join('');\n    renderSuper12Table();\n}")

# 3. renderSuper12Table fonksiyonunu dosyanin sonuna ekle
func_code = '''
function renderSuper12Table() {
    const tbody = document.getElementById('tb-super12-stocks');
    if (!tbody || !globalDashboardData || !globalDashboardData.all_symbols_stats) return;
    
    let allStats = Object.entries(globalDashboardData.all_symbols_stats).map(([sym, data]) => {
        let price = data.Price || data.Daily_Close || 0;
        let change = data.Change_Pct || 0;
        let volLot = data.Volume || 0;
        let volTL = volLot * price;
        
        let rVol = 0;
        let state = 'NONE';
        if (data.v8_discovery) {
            state = data.v8_discovery.state || 'NONE';
            if (data.v8_discovery.metrics) {
                rVol = data.v8_discovery.metrics.relative_volume || 0;
            }
        }
        
        let tScore = 50;
        if (change > 0 && change <= 7) tScore += (change * 3);
        else if (change > 7) tScore += 20;
        else if (change < 0) tScore += (change * 3);
        
        if (change > 0) {
            if (rVol > 1.5) tScore += 15;
            if (rVol > 2.5) tScore += 15;
            if (rVol < 0.8) tScore -= 15;
        } else if (change < 0) {
            if (rVol > 1.5) tScore -= 15;
            if (rVol > 2.5) tScore -= 15;
            if (rVol < 0.8) tScore += 10;
        }
        if (state === 'BREAKOUT') tScore += 20;
        else if (state === 'PRE_BREAKOUT') tScore += 15;
        tScore = Math.min(Math.max(tScore, 0), 100);

        let superScore = tScore + (rVol * 10);
        if (state === 'BREAKOUT') superScore += 50;
        if (state === 'PRE_BREAKOUT') superScore += 30;
        if (change > 9.9) superScore += 20;
        
        return {
            symbol: sym,
            price: price,
            change: change,
            volume_lot: volLot,
            volume_tl: volTL,
            rel_vol: rVol,
            tavan_score: tScore,
            super_score: superScore
        };
    });
    
    allStats.sort((a, b) => b.super_score - a.super_score);
    const top12 = allStats.slice(0, 12);
    
    tbody.innerHTML = top12.map((s, index) => {
        const color = s.change > 0 ? 'var(--accent-green)' : (s.change < 0 ? 'var(--accent-red)' : 'var(--text-color)');
        const sign = s.change > 0 ? '+' : '';
        const volLotM = (s.volume_lot / 1000000).toFixed(1) + 'M';
        const volTLM = (s.volume_tl / 1000000).toFixed(1) + 'M ?';
        const relVolPct = (s.rel_vol * 100).toFixed(0);
        const relVolText = s.change > 0 ? + % : (s.change < 0 ? - % : %);
        
        let scColor = '#ef4444'; 
        if (s.tavan_score >= 80) scColor = '#22c55e'; 
        else if (s.tavan_score >= 60) scColor = '#3b82f6'; 
        else if (s.tavan_score >= 40) scColor = '#f97316'; 
        let scoreBadge = <span style="font-weight:900; padding:3px 10px; border-radius:12px; background:22; color:; border:1px solid 66; min-width:35px; display:inline-block; text-align:center;"></span>;
        
        const sym = s.symbol.replace('.IS', '');
        let actionBtns = <button onclick="quickTradeBuy('')" style="background:rgba(34,197,94,0.2); color:#22c55e; border:1px solid rgba(34,197,94,0.5); border-radius:4px; padding:3px 10px; cursor:pointer; font-weight:bold; font-size:0.75rem; margin-right:4px; transition:0.2s;" onmouseover="this.style.background='#22c55e'; this.style.color='#fff';" onmouseout="this.style.background='rgba(34,197,94,0.2)'; this.style.color='#22c55e';">AL</button>
                          <button onclick="quickTradeBuy('')" style="background:rgba(239,68,68,0.2); color:#ef4444; border:1px solid rgba(239,68,68,0.5); border-radius:4px; padding:3px 10px; cursor:pointer; font-weight:bold; font-size:0.75rem; transition:0.2s;" onmouseover="this.style.background='#ef4444'; this.style.color='#fff';" onmouseout="this.style.background='rgba(239,68,68,0.2)'; this.style.color='#ef4444';">SAT</button>;
        
        let rankBadge = <span style="display:inline-block; width:20px; text-align:center; color:var(--text-muted); font-size:0.8rem; font-weight:bold; margin-right:5px;">#</span>;
        
        return 
            <tr>
                <td style="font-weight:bold; cursor:pointer; color:var(--text-light);" onclick="openGraphicTab('')"> </td>
                <td style="font-weight:600;">?</td>
                <td style="color:; font-weight:bold;">%</td>
                <td style="color:var(--text-muted);"></td>
                <td style="color:var(--text-muted);"></td>
                <td style="color:; font-weight:bold;"></td>
                <td></td>
                <td></td>
            </tr>
        ;
    }).join('');
}
'''
if 'function renderSuper12Table()' not in text:
    text += func_code

with open('ui/app.js', 'w', encoding='utf-8') as f:
    f.write(text)
print("APP JS PATCHED")
