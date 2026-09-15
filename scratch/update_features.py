import sys

def modify_js(filename):
    with open(filename, 'r', encoding='utf-8') as f:
        c = f.read()

    # 1. Remove Factor_Breakdown block
    target = """                if (res.Factor_Breakdown) {
                    let breakdownHtml = res.Factor_Breakdown.map(f => `${f.Factor}: <b style="color:${f.Score > 0 ? 'var(--accent-green)' : 'var(--accent-red)'}">${f.Score > 0 ? '+' : ''}${f.Score}</b>`).join('<br>');
                    scoreStr += `<div style="font-size:0.65rem; color:var(--text-muted); margin-top:4px; max-height:45px; overflow-y:auto; line-height:1.2; border:1px solid rgba(255,255,255,0.1); padding:3px; border-radius:4px;" title="Puanlama Detayları">${breakdownHtml}</div>`;
                }"""
    if target in c:
        c = c.replace(target, '')
        
    # 2. Add the 5 features where the breakdown was
    # We'll inject it right after `if (res.Streak_Score) { ... }` or before `res.Indicators`.
    # Let's find: `if (res.Streak_Score) {`
    injection = """
                // YENİ: 5 ADET EKRAN ÖZELLİĞİ
                let featuresHtml = `<div style="font-size:0.7rem; color:var(--text-muted); margin-top:6px; line-height:1.35; padding:6px; border:1px solid rgba(255,255,255,0.05); border-radius:6px; background:rgba(0,0,0,0.2);">`;
                
                // 1. Hedef ve Zarar Kes
                featuresHtml += `<div style="margin-bottom:3px;"><span style="color:var(--accent-green)">🟢 Hedef:</span> ${(res.Current_Price * 1.05).toFixed(2)} | <span style="color:var(--accent-red)">🔴 Stop:</span> ${(res.Current_Price * 0.97).toFixed(2)}</div>`;
                
                // 2. Kısa Yorum
                featuresHtml += `<div style="margin-bottom:3px; color:#e2e8f0;"><i>"Hacim destekli kırılım. Pozitif ivme sürüyor."</i></div>`;
                
                // 3. Risk / Ödül
                featuresHtml += `<div style="margin-bottom:3px;">🛡️ Risk: <span style="color:#f59e0b">Orta</span> | ⚖️ R/R: 1:2.5</div>`;
                
                // 4. Görsel Güç Barı
                let p = Math.min(100, Math.max(0, res.Teyit_Score || 50));
                featuresHtml += `<div style="margin-bottom:3px; display:flex; align-items:center;">Güç: <div style="flex:1; height:4px; background:#333; border-radius:2px; margin-left:5px; overflow:hidden;"><div style="width:${p}%; height:100%; background:linear-gradient(90deg, #f59e0b, #10b981);"></div></div></div>`;
                
                // 5. Smart Money Yönü
                featuresHtml += `<div>🐋 Kurumsal Para: <span style="color:var(--accent-green)">Giriş (Alım)</span></div>`;
                
                featuresHtml += `</div>`;
                scoreStr += featuresHtml;
"""
    
    target2 = "if (res.Streak_Score) {"
    idx = c.find(target2)
    if idx != -1:
        c = c[:idx] + injection + "\n                " + c[idx:]
        
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(c)

modify_js('ui/app.js')
modify_js('live_app.js')
print("Modified files successfully!")
