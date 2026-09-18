# -*- coding: utf-8 -*-
with open('ui/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

import re
old_thead = '''<thead>
                                <tr>
                                    <th style="cursor:pointer;" onclick="sortAllStocks('symbol')">Hisse |</th>
                                    <th style="cursor:pointer;" onclick="sortAllStocks('price')">Fiyat |</th>
                                    <th style="cursor:pointer;" onclick="sortAllStocks('change')">Deðiþim |</th>
                                    <th style="cursor:pointer;" onclick="sortAllStocks('volume_tl')">Hacim(TL) |</th>
                                    <th style="cursor:pointer;" onclick="sortAllStocks('volume_lot')">Hacim(Lot) |</th>
                                    <th>Durum / Saat</th>
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
                                    <th>Durum</th>
                                </tr>
                            </thead>'''
content = content.replace(old_thead, new_thead)
with open('ui/index.html', 'w', encoding='utf-8') as f:
    f.write(content)

with open('ui/app.js', 'r', encoding='utf-8') as f:
    appjs = f.read()

# JS içindeki renderAllStocksTable guncelle
new_map = r'''    let allStats = Object.entries(globalDashboardData.all_symbols_stats).map(([sym, data]) => {
        let price = data.Price || data.Daily_Close || 0;
        let change = data.Change_Pct || 0;
        let volLot = data.Volume || 0;
        let volTL = volLot * price;
        let rVol = (data.v8_discovery && data.v8_discovery.metrics && data.v8_discovery.metrics.relative_volume) ? data.v8_discovery.metrics.relative_volume : 0;
        return {
            symbol: sym,
            price: price,
            change: change,
            volume_lot: volLot,
            volume_tl: volTL,
            rel_vol: rVol,
            time: data.Time || '-',
            state: (data.v8_discovery && data.v8_discovery.state) ? data.v8_discovery.state : 'NONE'
        };
    });'''
appjs = re.sub(r'let allStats = Object\.entries\(globalDashboardData\.all_symbols_stats\)\.map.*?\n    \}\);\n', new_map + '\n', appjs, flags=re.DOTALL)

new_tr = r'''        const color = s.change > 0 ? 'var(--accent-green)' : (s.change < 0 ? 'var(--accent-red)' : 'var(--text-color)');
        const sign = s.change > 0 ? '+' : '';
        const volLotM = (s.volume_lot / 1000000).toFixed(1) + 'M';
        const volTLM = (s.volume_tl / 1000000).toFixed(1) + 'M ?';
        const relVolPct = (s.rel_vol * 100).toFixed(0);
        const relVolText = s.change > 0 ? + % : (s.change < 0 ? - % : %);
        
        const sym = s.symbol.replace('.IS', '');
        let stateBadge = '';
        if (s.state !== 'NONE' && s.state !== 'UNKNOWN') {
            stateBadge = <span style="font-size:0.7rem; background:rgba(255,255,255,0.1); padding:2px 5px; border-radius:4px;"></span>;
        }
        
        return 
            <tr>
                <td style="font-weight:bold; cursor:pointer; color:var(--text-light);" onclick="openGraphicTab('')"></td>
                <td style="font-weight:600;">?</td>
                <td style="color:; font-weight:bold;">%</td>
                <td style="color:var(--text-muted);"></td>
                <td style="color:var(--text-muted);"></td>
                <td style="color:; font-weight:bold;"></td>
                <td style="font-size:0.8rem; color:var(--text-muted);"></td>
            </tr>
        ;'''
appjs = re.sub(r'const color = s\.change > 0.*?</tr>\n        ;', new_tr, appjs, flags=re.DOTALL)

with open('ui/app.js', 'w', encoding='utf-8') as f:
    f.write(appjs)
print("UI_VOL_PCT_FIXED")
