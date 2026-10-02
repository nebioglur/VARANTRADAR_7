# -*- coding: utf-8 -*-
import codecs

with codecs.open('ui/app.js', 'r', 'utf-8') as f:
    text = f.read()

old_block = '''function renderAllStocksTable() {
    const tbody = document.getElementById('tb-all-stocks-home');
    if (!tbody || !globalDashboardData || !globalDashboardData.all_symbols_stats) return;
    
    let allStats = Object.entries(globalDashboardData.all_symbols_stats).map(([sym, data]) => ({
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
        return 
            <tr>
                <td style="font-weight:bold;"></td>
                <td>TL </td>
                <td style="color:; font-weight:bold;">%</td>
                <td>M</td>
                <td style="color:var(--text-muted);"></td>
            </tr>
        ;
    }).join('');
}'''

new_block = '''var currentStocksSort = { col: 'change', asc: false };

function sortAllStocks(col) {
    if (currentStocksSort.col === col) {
        currentStocksSort.asc = !currentStocksSort.asc;
    } else {
        currentStocksSort.col = col;
        currentStocksSort.asc = (col === 'symbol');
    }
    renderAllStocksTable();
}

function renderAllStocksTable() {
    const tbody = document.getElementById('tb-all-stocks-home');
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
        
        return {
            symbol: sym,
            price: price,
            change: change,
            volume_lot: volLot,
            volume_tl: volTL,
            rel_vol: rVol,
            tavan_score: tScore,
            time: data.Time || '-',
            state: state
        };
    });
    
    allStats.sort((a, b) => {
        let valA = a[currentStocksSort.col];
        let valB = b[currentStocksSort.col];
        if (typeof valA === 'string') valA = valA.toLowerCase();
        if (typeof valB === 'string') valB = valB.toLowerCase();
        
        if (valA < valB) return currentStocksSort.asc ? -1 : 1;
        if (valA > valB) return currentStocksSort.asc ? 1 : -1;
        return 0;
    });
    
    tbody.innerHTML = allStats.map(s => {
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
        
        return 
            <tr>
                <td style="font-weight:bold; cursor:pointer; color:var(--text-light);" onclick="openGraphicTab('')"></td>
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

function quickTradeBuy(sym) {
    const pfBtn = Array.from(document.querySelectorAll('.nav-btn')).find(b => b.getAttribute('href') && b.getAttribute('href').includes('portfolio'));
    if (pfBtn) switchMainTab('portfolio', pfBtn);
    
    setTimeout(() => {
        const symInput = document.getElementById('lt-symbol');
        if (symInput) {
            symInput.value = sym;
            symInput.dispatchEvent(new Event('input'));
        }
    }, 200);
}'''

if old_block in text:
    text = text.replace(old_block, new_block)
    with codecs.open('ui/app.js', 'w', 'utf-8') as f:
        f.write(text)
    print("SUCCESS: REPLACED CLEANLY")
else:
    print("ERROR: OLD BLOCK NOT FOUND")
