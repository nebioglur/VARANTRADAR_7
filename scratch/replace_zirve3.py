import sys
with open('ui/app.js', 'r', encoding='utf-8') as f:
    c = f.read()

idx_start = c.find('const maxG = item.max_gain_pct')
idx_end = c.find('</div>\\n                <div>${hitStatus}</div>', idx_start)
if idx_end == -1:
    idx_end = c.find('</div>\n                <div>${hitStatus}</div>', idx_start)

if idx_start == -1 or idx_end == -1:
    print('Indices not found')
    sys.exit(1)

new_code = """const maxG = item.max_gain_pct !== undefined ? item.max_gain_pct.toFixed(2) : (item.max_gain !== undefined ? item.max_gain : '-');

            let diffVal = 0;
            let diffPct = 0;
            if (item.closing_price && item.morning_price) {
                diffVal = item.closing_price - item.morning_price;
                diffPct = (diffVal / item.morning_price) * 100;
            }
            const diffColor = diffVal > 0 ? 'var(--accent-green)' : (diffVal < 0 ? 'var(--accent-red)' : 'var(--text-muted)');
            const diffStr = diffVal > 0 ? '+' + diffVal.toFixed(2) : diffVal.toFixed(2);
            const diffPctStr = diffPct > 0 ? '+' + diffPct.toFixed(2) : diffPct.toFixed(2);

            const hitStatus = item.hit_ceiling ? '<span style="background:rgba(16,185,129,0.2); color:#10b981; padding:2px 5px; border-radius:4px; font-size:0.7rem;"><i class="fa-solid fa-fire"></i> TAVAN</span>' : 
                               (item.hit_plus5 ? '<span style="background:rgba(245,158,11,0.2); color:#f59e0b; padding:2px 5px; border-radius:4px; font-size:0.7rem;">+%5</span>' : '');
            
            const card = document.createElement('div');
            card.className = 'history-card';
            card.innerHTML = `
                ${dt}
                <div style="font-size:1.1rem; font-weight:700; margin-bottom:10px; color:#fff;">${sym}</div>
                <div style="display:flex; justify-content:space-between; font-size:0.75rem; margin-bottom:4px; background:rgba(0,0,0,0.2); padding:4px; border-radius:4px;">
                    <span style="color:var(--text-muted);">Öneri:</span>
                    <span><b style="color:#fff;">${mPrice}</b> (<span style="color:${mColor}">${mPct > 0 ? '+' : ''}${mPct}%</span>)</span>
                </div>
                <div style="display:flex; justify-content:space-between; font-size:0.75rem; margin-bottom:4px; background:rgba(0,0,0,0.2); padding:4px; border-radius:4px;">
                    <span style="color:var(--text-muted);">Kapanış:</span>
                    <span><b style="color:#fff;">${cPrice}</b> (<span style="color:${cColor}">${cPct > 0 ? '+' : ''}${cPct}%</span>)</span>
                </div>
                <div style="display:flex; justify-content:space-between; font-size:0.75rem; margin-bottom:8px; background:rgba(0,0,0,0.2); padding:4px; border-radius:4px;">
                    <span style="color:var(--text-muted);">Net Getiri:</span>
                    <span style="color:${diffColor}; font-weight:bold;">${diffStr} ₺ (${diffPctStr}%)</span>
                """

c = c[:idx_start] + new_code + c[idx_end:]

with open('ui/app.js', 'w', encoding='utf-8') as f:
    f.write(c)
print('Replaced successfully by index')
