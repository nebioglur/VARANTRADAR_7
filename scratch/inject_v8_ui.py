import os

with open('ui/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Update the nav button to use switchMainTab('v8', this) instead of window.location.href
target_btn = 'window.location.href=\'/v8\''
if target_btn in text:
    text = text.replace('window.location.href=\'/v8\'', 'switchMainTab(\'v8\', this)')

# 2. Inject the v8-wrapper div before the guide-wrapper or before closing body
wrapper_html = """
    <!-- V8 ENGINE TAB -->
    <div id="v8-wrapper" class="main-wrapper" style="display:none; max-width:1400px; margin:0 auto; padding:1rem;">
        
        <div style="margin-bottom:2rem; text-align: center;">
            <h2 style="color:var(--accent-blue); font-size: 1.8rem; margin-bottom: 0.5rem;"><i class="fa-solid fa-brain"></i> V8 ENGINE (Otonom Karar Destek)</h2>
            <p style="color:var(--text-muted); font-size: 0.9rem;">Hareket başlamadan önce fark et, Kırılımı Doğrula, Tuzaktan Kaçın, Sonucu Öğren.</p>
        </div>

        <!-- MARKET REGIME WIDGET -->
        <div class="radar-card" style="margin-bottom: 1.5rem; text-align: center; padding: 1.5rem; border: 1px solid rgba(59, 130, 246, 0.3); background: rgba(15, 23, 42, 0.6);">
            <div style="font-size: 0.85rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 1px;">Piyasa Rejimi (XU100)</div>
            <div style="display: flex; justify-content: center; align-items: center; gap: 15px; margin-top: 10px;">
                <span id="regime-status" style="font-size: 1.8rem; font-weight: 800; padding: 5px 15px; border-radius: 8px; background: var(--bg-lighter);">YÜKLENİYOR...</span>
                <span id="regime-score" style="font-size: 1.2rem; color: var(--text-light);">--</span>
            </div>
            <div id="regime-trend" style="margin-top: 10px; font-size: 0.95rem;"></div>
        </div>

        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(350px, 1fr)); gap: 1.5rem; margin-bottom: 1.5rem;">
            
            <!-- DISCOVERY -->
            <div class="radar-card">
                <div class="card-header" style="border-bottom: 1px solid var(--border-color); padding-bottom: 10px; margin-bottom: 10px;">
                    <h3 style="color:var(--accent-blue); font-size:1.2rem; margin:0;"><i class="fa-solid fa-magnifying-glass"></i> Discovery (Hazırlık)</h3>
                    <div style="font-size:0.75rem; color:var(--text-muted); margin-top:4px;">Patlamadan önceki hacim ve volatilite sıkışmaları</div>
                </div>
                <div class="table-responsive">
                    <table class="data-table" style="width: 100%;">
                        <thead>
                            <tr>
                                <th>Hisse</th>
                                <th>Durum</th>
                                <th>Hazırlık Skoru</th>
                                <th>Hacim Şişmesi</th>
                            </tr>
                        </thead>
                        <tbody id="v8-discovery-tbody">
                            <tr><td colspan="4" style="text-align:center; color:var(--text-muted); padding:1rem;">Yükleniyor...</td></tr>
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- EXECUTION -->
            <div class="radar-card">
                <div class="card-header" style="border-bottom: 1px solid var(--border-color); padding-bottom: 10px; margin-bottom: 10px;">
                    <h3 style="color:var(--accent-green); font-size:1.2rem; margin:0;"><i class="fa-solid fa-bolt"></i> Execution (Kırılım & Giriş)</h3>
                    <div style="font-size:0.75rem; color:var(--text-muted); margin-top:4px;">Gerçekleşen kırılımlar ve tuzak riski filtresi</div>
                </div>
                <div class="table-responsive">
                    <table class="data-table" style="width: 100%;">
                        <thead>
                            <tr>
                                <th>Hisse</th>
                                <th>Kalite/Tuzak</th>
                                <th>V8 Kararı</th>
                                <th>Sebep</th>
                            </tr>
                        </thead>
                        <tbody id="v8-breakout-tbody">
                            <tr><td colspan="4" style="text-align:center; color:var(--text-muted); padding:1rem;">Yükleniyor...</td></tr>
                        </tbody>
                    </table>
                </div>
            </div>

        </div>

        <!-- OUTCOME LEARNING -->
        <div class="radar-card">
            <div class="card-header" style="border-bottom: 1px solid var(--border-color); padding-bottom: 10px; margin-bottom: 10px;">
                <h3 style="color:var(--accent-purple); font-size:1.2rem; margin:0;"><i class="fa-solid fa-brain"></i> Outcome & Learning (Sonuç Takibi)</h3>
                <div style="font-size:0.75rem; color:var(--text-muted); margin-top:4px;">V8 tarafından onaylanıp canlı takip edilen işlemlerin MFE/MAE sonuçları</div>
            </div>
            <div class="table-responsive" style="max-height: 400px; overflow-y: auto;">
                <table class="data-table" style="width: 100%; white-space: nowrap;">
                    <thead style="position: sticky; top: 0; background: var(--bg-base); z-index: 10;">
                        <tr>
                            <th>Tarih</th>
                            <th>Hisse</th>
                            <th>Giriş</th>
                            <th>T+5 dk</th>
                            <th>T+15 dk</th>
                            <th>T+30 dk</th>
                            <th>T+60 dk</th>
                            <th>MFE (Kâr)</th>
                            <th>MAE (Zarar)</th>
                            <th>Durum</th>
                        </tr>
                    </thead>
                    <tbody id="v8-learning-tbody">
                        <tr><td colspan="10" style="text-align:center; color:var(--text-muted); padding:1rem;">Yükleniyor...</td></tr>
                    </tbody>
                </table>
            </div>
        </div>

    </div>
"""

# Inject before guide-wrapper if possible, else append
if 'id="v8-wrapper"' not in text:
    guide_idx = text.find('<div id="guide-wrapper"')
    if guide_idx != -1:
        text = text[:guide_idx] + wrapper_html + "\n" + text[guide_idx:]
        
        # Write back
        with open('ui/index.html', 'w', encoding='utf-8') as f:
            f.write(text)
        print('Injected V8 wrapper into index.html')
    else:
        print('Could not find guide-wrapper to inject before')
else:
    print('V8 wrapper already injected')
