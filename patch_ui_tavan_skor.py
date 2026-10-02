# -*- coding: utf-8 -*-
import re

with open('ui/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Tablo basliklarini yenile
old_thead = '''<thead>
                                <tr>
                                    <th style="cursor:pointer;" onclick="sortAllStocks('symbol')">Hisse |</th>
                                    <th style="cursor:pointer;" onclick="sortAllStocks('price')">Fiyat |</th>
                                    <th style="cursor:pointer;" onclick="sortAllStocks('change')">Deðiþim |</th>
                                    <th style="cursor:pointer;" onclick="sortAllStocks('volume_tl')">Hacim(TL) |</th>
                                    <th style="cursor:pointer;" onclick="sortAllStocks('volume_lot')">Hacim(Lot) |</th>
                                    <th style="cursor:pointer;" onclick="sortAllStocks('rel_vol')">Hacim Gücü % |</th>
                                    <th>Durum</th>
                                </tr>
                            </thead>'''
new_thead = '''<thead>
                                <tr>
                                    <th style="cursor:pointer;" onclick="sortAllStocks('symbol')">Hisse |</th>
                                    <th style="cursor:pointer;" onclick="sortAllStocks('price')">Fiyat |</th>
                                    <th style="cursor:pointer;" onclick="sortAllStocks('change')">Deðiþim |</th>
                                    <th style="cursor:pointer;" onclick="sortAllStocks('volume_tl')">Hacim(TL) |</th>
                                    <th style="cursor:pointer;" onclick="sortAllStocks('volume_lot')">Hacim(Lot) |</th>
                                    <th style="cursor:pointer;" onclick="sortAllStocks('rel_vol')">Hacim Gücü % |</th>
                                    <th style="cursor:pointer;" onclick="sortAllStocks('tavan_score')">Tavan Skoru |</th>
                                    <th>Ýþlem</th>
                                </tr>
                            </thead>'''
content = content.replace(old_thead, new_thead)
with open('ui/index.html', 'w', encoding='utf-8') as f:
    f.write(content)

with open('ui/app.js', 'r', encoding='utf-8') as f:
    appjs = f.read()

# JS içindeki map guncelle
new_map = r'''    let allStats = Object.entries(globalDashboardData.all_symbols_stats).map(([sym, data]) => {
        let price = data.Price || data.Daily_Close || 0;
        let change = data.Change_Pct || 0;
        let volLot = data.Volume || 0;
        let volTL = volLot * price;
        let rVol = (data.v8_discovery && data.v8_discovery.metrics && data.v8_discovery.metrics.relative_volume) ? data.v8_discovery.metrics.relative_volume : 0;
        let state = (data.v8_discovery && data.v8_discovery.state) ? data.v8_discovery.state : 'NONE';
        
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
    });'''
appjs = re.sub(r'    let allStats = Object\.entries\(globalDashboardData\.all_symbols_stats\)\.map.*?\n    \}\);\n', new_map + '\n', appjs, flags=re.DOTALL)

new_tr = r'''        const color = s.change > 0 ? 'var(--accent-green)' : (s.change < 0 ? 'var(--accent-red)' : 'var(--text-color)');
        const sign = s.change > 0 ? '+' : '';
        const volLotM = (s.volume_lot / 1000000).toFixed(1) + 'M';
        const volTLM = (s.volume_tl / 1000000).toFixed(1) + 'M ?';
        const relVolPct = (s.rel_vol * 100).toFixed(0);
        const relVolText = s.change > 0 ? + % : (s.change < 0 ? - % : %);
        
        let scColor = '#ef4444'; // Red
        if (s.tavan_score >= 80) scColor = '#22c55e'; // Green
        else if (s.tavan_score >= 60) scColor = '#3b82f6'; // Blue
        else if (s.tavan_score >= 40) scColor = '#f97316'; // Orange
        let scoreBadge = <span style="font-weight:900; padding:2px 8px; border-radius:12px; background:22; color:; border:1px solid 66;"></span>;
        
        const sym = s.symbol.replace('.IS', '');
        let actionBtns = <button onclick="quickTradeBuy('')" style="background:#22c55e; color:white; border:none; border-radius:4px; padding:3px 8px; cursor:pointer; font-weight:bold; font-size:0.7rem; margin-right:4px;">AL</button>
                          <button onclick="quickTradeBuy('')" style="background:#ef4444; color:white; border:none; border-radius:4px; padding:3px 8px; cursor:pointer; font-weight:bold; font-size:0.7rem;">SAT</button>;
        
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
        ;'''
appjs = re.sub(r'        const color = s\.change > 0.*?</tr>\n        ;', new_tr, appjs, flags=re.DOTALL)

# JS'ye quickTradeBuy fonksiyonu ekle
quick_trade = r'''
function quickTradeBuy(sym) {
    const pfBtn = Array.from(document.querySelectorAll('.nav-btn')).find(b => b.getAttribute('href') && b.getAttribute('href').includes('portfolio'));
    if (pfBtn) switchMainTab('portfolio', pfBtn);
    else switchMainTab('portfolio', document.querySelector('.nav-btn'));
    
    setTimeout(() => {
        const symInput = document.getElementById('lt-symbol');
        if (symInput) {
            symInput.value = sym;
            symInput.dispatchEvent(new Event('input'));
        }
    }, 200);
}
'''
if "function quickTradeBuy(" not in appjs:
    appjs += quick_trade

with open('ui/app.js', 'w', encoding='utf-8') as f:
    f.write(appjs)
print("UI_TAVAN_SKOR_FIXED")
