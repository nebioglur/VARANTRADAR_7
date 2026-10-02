import sys

with open('ui/app.js', 'r', encoding='utf-8') as f:
    c = f.read()

# 1. ADD SORTING AND COUNTS
target1 = """    title.innerHTML = titleText;
    content.innerHTML = '';
    
    if (items.length === 0) {"""
replacement1 = """    
    let posCount = 0;
    let negCount = 0;
    
    if (items.length > 0) {
        // Sort items by Net Getiri (Percentage) Descending
        items.sort((a, b) => {
            let pctA = a.morning_price ? ((a.closing_price || 0) - a.morning_price) / a.morning_price : 0;
            let pctB = b.morning_price ? ((b.closing_price || 0) - b.morning_price) / b.morning_price : 0;
            return pctB - pctA;
        });
        
        // Count positive and negative net returns
        items.forEach(it => {
            let diff = (it.closing_price || 0) - (it.morning_price || 0);
            if (diff > 0) posCount++;
            else if (diff < 0) negCount++;
        });
        
        titleText += `<div style="font-size:0.8rem; margin-top:8px; color:var(--text-muted); font-weight:normal; display:flex; gap:10px; align-items:center;">
            <span style="background:rgba(16,185,129,0.1); color:var(--accent-green); padding:2px 8px; border-radius:12px;"><i class="fa-solid fa-arrow-trend-up"></i> ${posCount} Kazanç</span>
            <span style="background:rgba(239,68,68,0.1); color:var(--accent-red); padding:2px 8px; border-radius:12px;"><i class="fa-solid fa-arrow-trend-down"></i> ${negCount} Kayıp</span>
        </div>`;
    }

    title.innerHTML = titleText;
    content.innerHTML = '';
    
    if (items.length === 0) {"""

if target1 in c:
    c = c.replace(target1, replacement1)
    print("Replaced sorting and counts successfully")
else:
    print("Target 1 not found")

# 2. FIX CLOSING PCT
target2 = """            const cPrice = item.closing_price ? item.closing_price.toFixed(2) : '-';
            const cPct = item.closing_gain_pct !== undefined ? item.closing_gain_pct.toFixed(2) : '-';
            const cColor = item.closing_gain_pct > 0 ? 'var(--accent-green)' : (item.closing_gain_pct < 0 ? 'var(--accent-red)' : 'var(--text-muted)');"""
replacement2 = """            // Calculate True Daily Closing Percentage
            let p_close = item.morning_price || 0;
            if (item.morning_gain_pct !== undefined && item.morning_gain_pct !== 0) {
                p_close = item.morning_price / (1 + (item.morning_gain_pct / 100));
            }
            let trueCPct = 0;
            if (p_close > 0 && item.closing_price) {
                trueCPct = ((item.closing_price - p_close) / p_close) * 100;
            }
            const cPrice = item.closing_price ? item.closing_price.toFixed(2) : '-';
            const cPct = trueCPct.toFixed(2);
            const cColor = trueCPct > 0 ? 'var(--accent-green)' : (trueCPct < 0 ? 'var(--accent-red)' : 'var(--text-muted)');"""

if target2 in c:
    c = c.replace(target2, replacement2)
    print("Replaced cPct calculation successfully")
else:
    print("Target 2 not found")
    
with open('ui/app.js', 'w', encoding='utf-8') as f:
    f.write(c)
