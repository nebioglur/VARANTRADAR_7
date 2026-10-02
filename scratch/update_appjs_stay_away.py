import re

with open('ui/app.js', 'r', encoding='utf-8') as f:
    c = f.read()

# 1. Update the table list
old_list = """                ["tb-signals-5m", "tb-tavan-adaylari", "tb-opportunities-1h", "tb-opportunities", "tb-gainers", "tb-losers", "tb-favorites", "tb-high_volume", "tb-low_volume"].forEach(id => {"""
new_list = """                ["tb-signals-5m", "tb-tavan-adaylari", "tb-opportunities-1h", "tb-stay-away-1h", "tb-opportunities", "tb-gainers", "tb-losers", "tb-favorites", "tb-high_volume", "tb-low_volume"].forEach(id => {"""
c = c.replace(old_list, new_list)

# 2. Update cats dict
old_cats = """        'opportunities_1h': 'tb-opportunities-1h',
        'opportunities': 'tb-opportunities',"""
new_cats = """        'opportunities_1h': 'tb-opportunities-1h',
        'stay_away_1h': 'tb-stay-away-1h',
        'opportunities': 'tb-opportunities',"""
c = c.replace(old_cats, new_cats)

# 3. Update header time span id logic
old_header = """const headerTimeSpan = document.getElementById('time-' + (cat === 'opportunities_1h' ? 'opportunities-1h' : cat));"""
new_header = """const headerTimeSpan = document.getElementById('time-' + (cat === 'opportunities_1h' ? 'opportunities-1h' : (cat === 'stay_away_1h' ? 'stay-away-1h' : cat)));"""
c = c.replace(old_header, new_header)

# 4. Add render logic
old_render = """            } else if (cat === 'opportunities_1h') {
                let s5 = res.Score_5 !== undefined ? res.Score_5 : 0;
                let sColor = s5 === 5 ? 'var(--accent-green)' : (s5 >= 4 ? 'var(--accent-blue)' : 'var(--accent-yellow)');
                scoreContent = `<span style="color:${sColor};font-weight:700;">${s5} / 5</span>`;
                
                if (res.Daily_Change_Pct !== undefined) {
                    let d_pct = parseFloat(res.Daily_Change_Pct);
                    let d_c = d_pct > 0 ? "var(--accent-green)" : (d_pct < 0 ? "var(--accent-red)" : "var(--text-muted)");
                    let d_sign = d_pct > 0 ? "+" : "";
                    priceStr += `<br><span style="color:${d_c}; font-size:0.75rem;">(${d_sign}%${Math.abs(d_pct).toFixed(2)})</span>`;
                }
                
                let barsAgoMain = res.Crossover_Bars_Ago !== undefined ? res.Crossover_Bars_Ago : '?';
                statusStr = `<span style="font-size:0.75rem; color:var(--text-muted);">🔀 ${barsAgoMain}s önce | ADX:${res.ADX_Val} RSI:${res.RSI_Val}</span>`;
            } else {"""

new_render = """            } else if (cat === 'opportunities_1h') {
                let s5 = res.Score_5 !== undefined ? res.Score_5 : 0;
                let sColor = s5 === 5 ? 'var(--accent-green)' : (s5 >= 4 ? 'var(--accent-blue)' : 'var(--accent-yellow)');
                scoreContent = `<span style="color:${sColor};font-weight:700;">${s5} / 5</span>`;
                
                if (res.Daily_Change_Pct !== undefined) {
                    let d_pct = parseFloat(res.Daily_Change_Pct);
                    let d_c = d_pct > 0 ? "var(--accent-green)" : (d_pct < 0 ? "var(--accent-red)" : "var(--text-muted)");
                    let d_sign = d_pct > 0 ? "+" : "";
                    priceStr += `<br><span style="color:${d_c}; font-size:0.75rem;">(${d_sign}%${Math.abs(d_pct).toFixed(2)})</span>`;
                }
                
                let barsAgoMain = res.Crossover_Bars_Ago !== undefined ? res.Crossover_Bars_Ago : '?';
                statusStr = `<span style="font-size:0.75rem; color:var(--text-muted);">🔀 ${barsAgoMain}s önce | ADX:${res.ADX_Val} RSI:${res.RSI_Val}</span>`;
            } else if (cat === 'stay_away_1h') {
                let s5 = res.Score_5 !== undefined ? res.Score_5 : 0;
                let sColor = s5 === 5 ? 'var(--accent-red)' : (s5 >= 4 ? '#f87171' : 'var(--accent-yellow)');
                scoreContent = `<span style="color:${sColor};font-weight:700;">${s5} / 5</span>`;
                
                if (res.Daily_Change_Pct !== undefined) {
                    let d_pct = parseFloat(res.Daily_Change_Pct);
                    let d_c = d_pct > 0 ? "var(--accent-green)" : (d_pct < 0 ? "var(--accent-red)" : "var(--text-muted)");
                    let d_sign = d_pct > 0 ? "+" : "";
                    priceStr += `<br><span style="color:${d_c}; font-size:0.75rem;">(${d_sign}%${Math.abs(d_pct).toFixed(2)})</span>`;
                }
                
                let barsAgoMain = res.Crossover_Bars_Ago !== undefined ? res.Crossover_Bars_Ago : '?';
                statusStr = `<span style="font-size:0.75rem; color:var(--text-muted);">📉 ${barsAgoMain}s önce | ADX:${res.ADX_Val} RSI:${res.RSI_Val}</span>`;
            } else {"""

c = c.replace(old_render, new_render)

with open('ui/app.js', 'w', encoding='utf-8') as f:
    f.write(c)
print('SUCCESS')
