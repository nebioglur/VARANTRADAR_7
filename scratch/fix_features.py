import sys
import re

def fix_js(filename):
    with open(filename, 'r', encoding='utf-8') as f:
        c = f.read()

    # We need to replace the static block we injected earlier.
    target_start_marker = "// YENİ: 5 ADET EKRAN ÖZELLİĞİ"
    target_end_marker = "scoreStr += featuresHtml;"
    
    idx_start = c.find(target_start_marker)
    idx_end = c.find(target_end_marker, idx_start)
    if idx_start != -1 and idx_end != -1:
        # The block to inject
        new_block = """// YENİ: 5 ADET EKRAN ÖZELLİĞİ (DİNAMİK)
                let featuresHtml = `<div style="font-size:0.7rem; color:var(--text-muted); margin-top:6px; line-height:1.35; padding:6px; border:1px solid rgba(255,255,255,0.05); border-radius:6px; background:rgba(0,0,0,0.2);">`;
                
                let p_val = parseFloat(res.Price || 0);
                
                // 1. Hedef ve Zarar Kes
                if (p_val > 0) {
                    featuresHtml += `<div style="margin-bottom:3px;"><span style="color:var(--accent-green)">🟢 Hedef:</span> ${(p_val * 1.05).toFixed(2)} | <span style="color:var(--accent-red)">🔴 Stop:</span> ${(p_val * 0.97).toFixed(2)}</div>`;
                }
                
                // 2. Kısa Yorum (Dinamik)
                let ai_comment = "Yatay seyir izleniyor.";
                let risk_level = "Orta";
                let risk_color = "#f59e0b";
                let smart_money = "Nötr";
                let sm_color = "var(--text-muted)";
                
                if (res.Indicators && res.Indicators.RSI) {
                    let rsi = res.Indicators.RSI;
                    if (rsi > 65) {
                        ai_comment = "RSI aşırı alım bölgesinde, kâr satışına dikkat.";
                        risk_level = "Yüksek";
                        risk_color = "var(--accent-red)";
                    } else if (rsi < 40) {
                        ai_comment = "Aşırı satım bölgesinden tepki potansiyeli.";
                        risk_level = "Düşük";
                        risk_color = "var(--accent-green)";
                    } else if (rsi >= 50 && rsi <= 55) {
                        ai_comment = "RSI 55 seviyesine yaklaşıyor, ivme artabilir.";
                    } else if (rsi > 55 && rsi <= 65) {
                        ai_comment = "RSI pozitif bölgede, yükseliş trendi teyitli.";
                    }
                    
                    if (res.Indicators.MACD_Positive && rsi < 65) {
                        smart_money = "Giriş (Alım)";
                        sm_color = "var(--accent-green)";
                        if (rsi >= 50 && rsi <= 55) ai_comment += " (MACD pozitif kesişim)";
                    } else if (!res.Indicators.MACD_Positive) {
                        smart_money = "Çıkış (Satış)";
                        sm_color = "var(--accent-red)";
                    }
                }
                
                if (res.Teyit_Score >= 80) {
                    smart_money = "Güçlü Giriş (Alım)";
                    sm_color = "var(--accent-green)";
                }
                
                featuresHtml += `<div style="margin-bottom:3px; color:#e2e8f0;"><i>"${ai_comment}"</i></div>`;
                
                // 3. Risk / Ödül
                featuresHtml += `<div style="margin-bottom:3px;">🛡️ Risk: <span style="color:${risk_color}">${risk_level}</span> | ⚖️ R/R: 1:2.5</div>`;
                
                // 4. Görsel Güç Barı
                let p = Math.min(100, Math.max(0, res.Teyit_Score || 50));
                let bar_color = p >= 70 ? '#10b981' : (p >= 40 ? '#f59e0b' : '#ef4444');
                featuresHtml += `<div style="margin-bottom:3px; display:flex; align-items:center;">Güç: <div style="flex:1; height:4px; background:#333; border-radius:2px; margin-left:5px; overflow:hidden;"><div style="width:${p}%; height:100%; background:linear-gradient(90deg, transparent, ${bar_color});"></div></div></div>`;
                
                // 5. Smart Money Yönü
                featuresHtml += `<div>🐋 Kurumsal Para: <span style="color:${sm_color}">${smart_money}</span></div>`;
                
                featuresHtml += `</div>`;
                scoreStr += featuresHtml;"""
                
        c = c[:idx_start] + new_block + c[idx_end + len(target_end_marker):]
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(c)
        print(f"Updated {filename}")

fix_js('ui/app.js')
fix_js('live_app.js')
