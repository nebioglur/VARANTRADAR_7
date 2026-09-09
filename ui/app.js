// ========== STATE MANAGEMENT ==========
let acTimeout = null;
let acSelectedIndex = -1;
let acItems = [];
let chartInstance = null;
let svrChartInstance = null;
let currentProjections = null;

// Chart State
window.globalCharts = [];
window.globalSeries = {};
window.globalChartData = null;

function resetChartView() {
    if (window.globalCharts && window.globalCharts.length > 0) {
        window.globalCharts.forEach(c => c.timeScale().fitContent());
    }
}

// ========== DOM ELEMENTS ==========
function setElText(id, text) {
    const el = document.getElementById(id);
    if (el) {
        if (el.tagName === 'INPUT') el.value = text;
        else el.textContent = text;
    }
}

const symbolInput = document.getElementById("symbol-input");
const acDropdown = document.getElementById("ac-dropdown");

// ========== AUTOCOMPLETE LOGIC ==========
symbolInput.addEventListener("input", function() {
    clearTimeout(acTimeout);
    const q = this.value.trim();
    acSelectedIndex = -1;
    if (q.length < 1) { acDropdown.style.display = 'none'; return; }
    
    acTimeout = setTimeout(async () => {
        try {
            const res = await fetch('/api/autocomplete?q=' + q);
            const matches = await res.json();
            if (matches.length === 0) { acDropdown.style.display = 'none'; return; }
            
            acDropdown.innerHTML = '';
            acItems = [];
            matches.forEach((m, index) => {
                let div = document.createElement('div');
                div.className = 'ac-item';
                div.innerText = m;
                div.dataset.index = index;
                div.onclick = function() {
                    symbolInput.value = m;
                    acDropdown.style.display = 'none';
                    analyzeSymbol();
                };
                acItems.push(div);
                acDropdown.appendChild(div);
            });
            acDropdown.style.display = 'block';
        } catch(e) { acDropdown.style.display = 'none'; }
    }, 200);
});

document.addEventListener('click', function(e) {
    if (!e.target.closest('.search-container')) acDropdown.style.display = 'none';
});

symbolInput.addEventListener("keydown", function(event) {
    if (acDropdown.style.display === 'block' && acItems.length > 0) {
        if (event.key === "ArrowDown") {
            event.preventDefault();
            acSelectedIndex++;
            if (acSelectedIndex >= acItems.length) acSelectedIndex = 0;
            updateAcSelection();
        } else if (event.key === "ArrowUp") {
            event.preventDefault();
            acSelectedIndex--;
            if (acSelectedIndex < 0) acSelectedIndex = acItems.length - 1;
            updateAcSelection();
        } else if (event.key === "Enter") {
            event.preventDefault();
            if (acSelectedIndex > -1 && acSelectedIndex < acItems.length) {
                symbolInput.value = acItems[acSelectedIndex].innerText;
            }
            acDropdown.style.display = 'none';
            analyzeSymbol();
        }
    } else if (event.key === "Enter") {
        event.preventDefault();
        acDropdown.style.display = 'none';
        analyzeSymbol();
    }
});

function updateAcSelection() {
    acItems.forEach((item, idx) => {
        if (idx === acSelectedIndex) {
            item.classList.add('selected');
            item.scrollIntoView({block: 'nearest'});
        } else {
            item.classList.remove('selected');
        }
    });
}

// ========== TAB & NAVIGATION LOGIC ==========
let lastActiveTab = 'home';
let analysisAbortController = null;
let logInterval = null;

// ============================================================
// <span style="color:#22c55e">●</span> ONLİNE KULLANICI SAYACI (Heartbeat)
// ============================================================
let _heartbeatSid = localStorage.getItem('varant-sid') || '';

async function sendHeartbeat() {
    try {
        const res = await fetch('/api/heartbeat', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ sid: _heartbeatSid })
        });
        const data = await res.json();
        if (data.sid) {
            _heartbeatSid = data.sid;
            localStorage.setItem('varant-sid', data.sid);
        }
        const el = document.getElementById('online-count');
        if (el && data.online !== undefined) {
            el.textContent = data.online;
        }
    } catch(e) { /* sessiz hata */ }
}

// Sayfa yüklenince hemen gönder, sonra 15 saniyede bir
sendHeartbeat();
setInterval(sendHeartbeat, 15000);

// ============================================================
// 🌗 TEMA TOGGLE (Koyu / Açık)
// ============================================================
function toggleTheme() {
    const body = document.body;
    const icon = document.getElementById('theme-icon');
    const label = document.getElementById('theme-label');
    const isLight = body.classList.toggle('light-mode');

    if (isLight) {
        if (icon) { icon.className = 'fa-solid fa-moon'; }
        if (label) label.textContent = 'Koyu Tema';
        localStorage.setItem('varant-theme', 'light');
    } else {
        if (icon) { icon.className = 'fa-solid fa-sun'; }
        if (label) label.textContent = 'Açık Tema';
        localStorage.setItem('varant-theme', 'dark');
    }
}

// Sayfa yüklenince tema tercihini geri yükle
(function initTheme() {
    const saved = localStorage.getItem('varant-theme');
    if (saved === 'light') {
        document.body.classList.add('light-mode');
        const icon = document.getElementById('theme-icon');
        const label = document.getElementById('theme-label');
        if (icon) icon.className = 'fa-solid fa-moon';
        if (label) label.textContent = 'Koyu Tema';
    }
})();

// ============================================================
// 🏆 GİRİŞ SAYFASI: Başarı Karnesi → Gerçek API Verisi
// ============================================================
async function fetchHomeWinrateStats() {
    try {
        const res = await fetch('/api/tavan_history?start_date=2026-08-04');
        const data = await res.json();
        const s = (data.status === 'success' && data.summary) ? data.summary : null;

        const el = (id) => document.getElementById(id);

        if (s && s.total_days_tracked > 0) {
            // 3 Ana KPI
            const fields = [
                ['stat-winrate', `%${s.tavan_success_pct}`],
                ['stat-winrate-sub', `${s.total_hit_ceiling}/${s.total_candidates_tracked} Tavan`],
                ['stat-avgprofit', `%${s.plus5_success_pct}`],
                ['stat-avgprofit-sub', `${s.total_hit_plus5}/${s.total_candidates_tracked} Hisse`],
                ['stat-pfactor', `+%${s.cumulative_avg_max_gain_pct}`],
                ['stat-pfactor-sub', `Ort. Zirve Getirisi`],
                ['stat-days-val', `${s.total_days_tracked} Gün / ${s.total_candidates_tracked} Öneri`],
                ['stat-warrant-val', `+%${s.ahlatci_warrant_avg_gain_pct}`],
                ['stat-close-val', `+%${s.cumulative_avg_closing_gain_pct}`]
            ];
            
            fields.forEach(([id, val]) => {
                if (el(id)) el(id).textContent = val;
                if (el(id + '-stats')) el(id + '-stats').textContent = val;
            });
        } else {
            // Veri yok — 04 Ağustos'tan önce
            const emptyFields = [
                ['stat-winrate', '-'],
                ['stat-winrate-sub', 'Veri bekleniyor'],
                ['stat-avgprofit', '-'],
                ['stat-avgprofit-sub', 'Veri bekleniyor'],
                ['stat-pfactor', '-'],
                ['stat-pfactor-sub', 'Veri bekleniyor'],
                ['stat-days-val', '04 Ağu 2026 sabahından itibaren'],
                ['stat-warrant-val', 'Bekleniyor'],
                ['stat-close-val', 'Bekleniyor']
            ];
            
            emptyFields.forEach(([id, val]) => {
                if (el(id)) el(id).textContent = val;
                if (el(id + '-stats')) el(id + '-stats').textContent = val;
            });
        }
    } catch (e) {
        console.warn('[WinrateStats] Veri alinamadi:', e.message);
    }
}


function switchMainTab(tabName, btnElement) {
    if (tabName !== 'dashboard') {
        lastActiveTab = tabName;
    }
    const loadingEl = document.getElementById('loading');
    if (loadingEl && tabName !== 'dashboard') loadingEl.style.display = 'none';

    document.getElementById('home-wrapper').style.display = tabName === 'home' ? 'block' : 'none';
    const dtWrapper = document.getElementById('detective-wrapper');
    if (dtWrapper) dtWrapper.style.display = tabName === 'detective' ? 'block' : 'none';
    document.getElementById('dashboard-wrapper').style.display = tabName === 'dashboard' ? 'block' : 'none';
    document.getElementById('radar-wrapper').style.display = tabName === 'radar' ? 'block' : 'none';
    document.getElementById('news-wrapper').style.display = tabName === 'news' ? 'block' : 'none';
    
    const statsWrapper = document.getElementById('stats-wrapper');
    if (statsWrapper) statsWrapper.style.display = tabName === 'stats' ? 'block' : 'none';
    
    const varantWrapper = document.getElementById('varant-wrapper');
    if (varantWrapper) varantWrapper.style.display = tabName === 'varant' ? 'block' : 'none';
    
    const simWrapper = document.getElementById('simulation-wrapper');
    if (simWrapper) simWrapper.style.display = tabName === 'simulation' ? 'block' : 'none';

    const pfWrapper = document.getElementById('portfolio-wrapper');
    if (pfWrapper) pfWrapper.style.display = tabName === 'portfolio' ? 'block' : 'none';

    const lbWrapper = document.getElementById('leaderboard-wrapper');
    if (lbWrapper) lbWrapper.style.display = tabName === 'leaderboard' ? 'block' : 'none';

    const logsWrapper = document.getElementById('logs-wrapper');
    if (logsWrapper) logsWrapper.style.display = tabName === 'logs' ? 'block' : 'none';

    const guideWrapper = document.getElementById('guide-wrapper');
    if (guideWrapper) guideWrapper.style.display = tabName === 'guide' ? 'block' : 'none';
    
    const btWrapper = document.getElementById('backtest-wrapper');
    if (btWrapper) btWrapper.style.display = tabName === 'backtest' ? 'block' : 'none';
    
    document.querySelectorAll('.nav-btn').forEach(btn => btn.classList.remove('active'));
    if (btnElement) btnElement.classList.add('active');
    
    // Alt navigasyon barı sadece dashboard/radar/stats/sim varken kullanışlı
    const bottomBar = document.querySelector('.bottom-mobile-bar');
    if (bottomBar) {
        bottomBar.style.display = (tabName === 'dashboard' || tabName === 'radar' || tabName === 'stats' || tabName === 'simulation' || tabName === 'varant') ? 'flex' : 'none';
    }

    if (tabName === 'detective') {
        fetchDetective();
    }
    if (tabName === 'radar') {
        startRadar('all');
    }
    if (tabName === 'stats') {
        fetchStatsTabData();
    }
    if (tabName === 'varant') {
        fetchVarantDashboardData();
    }
    if (tabName === 'simulation') {
        fetchSimulationData();
    }
    if (tabName === 'portfolio') {
        fetchLiveTerminal();
        ltRefreshResetUI();
        fetchAdminResetRequests();
    }
    if (tabName === 'leaderboard') {
        fetchLeaderboard();
    }
    if (tabName === 'logs') {
        fetchLogs();
    }

    // Aktif sekmenin adini URL hash'ine yaz (yenileme/derin link icin)
    try { if (history.replaceState) history.replaceState(null, '', '#' + tabName); } catch (e) {}
}

// Ust menu linki: normal sol tik sayfa icinde sekmeyi degistirir.
// Ctrl+tik / orta tik / sag tik -> tarayicinin dogal "yeni sekmede ac" menusu calisir
// (linkler /#sekme adresine yonlendigi icin yeni sekme dogru bolumle acilir).
function navClick(ev, tabName, el) {
    if (ev.button !== 0 || ev.ctrlKey || ev.metaKey || ev.shiftKey || ev.altKey) {
        return true; // tarayici varsayilani
    }
    ev.preventDefault();
    try { switchMainTab(tabName, el); } catch (e) { /* sessiz */ }
    return false;
}

// Sayfa /#sekme adi ile acildiysa dogru bolumu yukle (yeni sekmeden gelen linkler)
// DOM hazir olunca calistirilir ki sonradan eklenen sarmalayicilar da uygulanmis olsun.
function initTabFromHash() {
    const h = (location.hash || '').replace('#', '').trim();
    if (!h) return;
    const btn = Array.from(document.querySelectorAll('.nav-btn')).find(b => (b.getAttribute('href') || '').endsWith('#' + h) || (b.getAttribute('onclick') || '').includes("'" + h + "'"));
    if (btn) {
        try { switchMainTab(h, btn); } catch (e) { /* varsayilan sekmede kal */ }
    }
}
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initTabFromHash);
} else {
    initTabFromHash();
}

function cancelLoadingAndGoBack() {
    if (analysisAbortController) {
        try { analysisAbortController.abort(); } catch(e){}
    }
    if (logInterval) {
        clearInterval(logInterval);
    }
    const loadingEl = document.getElementById('loading');
    if (loadingEl) loadingEl.style.display = 'none';
    
    let targetTab = lastActiveTab || 'home';
    let navBtns = document.querySelectorAll('.nav-btn');
    let targetBtn = navBtns[0]; // GİRİŞ
    if (targetTab === 'radar' && navBtns.length > 4) {
        targetBtn = navBtns[4];
    } else if (targetTab === 'news' && navBtns.length > 5) {
        targetBtn = navBtns[5];
    }
    switchMainTab(targetTab, targetBtn);
}

function switchSubTab(tabName, btnElement) {
    document.querySelectorAll('#dashboard-wrapper .tab-pane').forEach(pane => pane.style.display = 'none');
    document.getElementById('tab-' + tabName).style.display = 'block';
    
    document.querySelectorAll('#dashboard-wrapper .s-tab').forEach(btn => btn.classList.remove('active'));
    if(btnElement) btnElement.classList.add('active');
    
    if (tabName === 'akd') {
        const symbol = document.getElementById('tk-sym').innerText;
        if (symbol && symbol !== 'SEMBOL') {
            fetchAKDData(symbol);
        }
    }
}

function switchRadarTab(tabName, btnElement) {
    document.querySelectorAll('#radar-wrapper .tab-pane').forEach(pane => {
        pane.classList.remove('active');
        pane.style.display = 'none';
    });
    const targetPane = document.getElementById('rtab-' + tabName);
    if (targetPane) {
        targetPane.classList.add('active');
        targetPane.style.display = 'block';
    }
    
    document.querySelectorAll('#radar-wrapper .s-tab').forEach(btn => btn.classList.remove('active'));
    if (btnElement) btnElement.classList.add('active');

    // Otomatik Yükleme & Tarama: Sekme açıldığında boş kalmaması için otomatik çalıştır
    if (tabName === 'opportunities1h') {
        const opp1hTbody = document.getElementById('opp1h-tbody');
        if (globalDashboardData && globalDashboardData['opportunities_1h'] && globalDashboardData['opportunities_1h'].length > 0) {
            renderAllDashboardTables();
        }
    } else {
        const tbodyEl = document.getElementById(tabName + '-tbody');
        const resultsEl = document.getElementById(tabName + '-results');
        const loadingEl = document.getElementById(tabName + '-loading');
        // Henüz sonuç yoksa ve şu an taranmıyorsa otomatik başlat
        if (tbodyEl && (!tbodyEl.children.length || resultsEl?.style.display === 'none') && loadingEl?.style.display !== 'block') {
            startRadar(tabName);
        }
    }
}

let currentHomeOppsTab = 'bist30';

function switchHomeOppsTab(tabName, btnElement) {
    currentHomeOppsTab = tabName;
    document.querySelectorAll('#home-wrapper .d-tab').forEach(btn => btn.classList.remove('active'));
    if(btnElement) btnElement.classList.add('active');
    
    const contentBox = document.getElementById('home-opps-content');
    contentBox.innerHTML = `
        <div style="text-align: center; padding: 2rem 0;">
            <p style="color:var(--text-muted); margin-bottom: 1rem;">Anlık taramayı başlatmak için butona tıklayın.</p>
            <button class="btn-primary" id="btn-scan-home" onclick="scanHomeOpportunities()">Fırsatları Canlı Tara</button>
        </div>
    `;
}

async function scanHomeOpportunities() {
    const contentBox = document.getElementById('home-opps-content');
    contentBox.innerHTML = `<div style="text-align:center; padding: 2rem 0;"><div class="spinner small"></div><p style="margin-top:1rem;color:var(--text-muted)">Yapay zeka analiz ediyor... Lütfen bekleyin.</p></div>`;
    
    let endpoint = '/api/scan';
    if (currentHomeOppsTab === 'bist50') endpoint = '/api/scan_bist50';
    else if (currentHomeOppsTab === 'yildiz') endpoint = '/api/scan_yildiz';
    else if (currentHomeOppsTab === 'all') endpoint = '/api/scan_all';
    
    try {
        const res = await fetch(endpoint);
        const data = await res.json();
        
        if (data.status === 'success' && data.results.length > 0) {
            contentBox.innerHTML = ""; // clear
            
            // Get top 3
            const top3 = data.results.slice(0, 3);
            top3.forEach((item, index) => {
                let scoreValue = item.Score !== undefined ? item.Score : (item.Confidence_Score !== undefined ? item.Confidence_Score : 0);
                let c = "bull";
                let l = "GÜÇLÜ AL";
                if (scoreValue >= 75) {
                    c = "bull";
                    l = "GÜÇLÜ AL (LİDER)";
                } else if (scoreValue >= 60) {
                    c = "base";
                    l = "KADEMELİ AL (DESTEK)";
                } else {
                    c = "bear";
                    l = "İZLE / BEKLE";
                }
                
                contentBox.innerHTML += `
                <div class="scenario-box ${c}" style="cursor:pointer;" onclick="document.getElementById('symbol-input').value='${item.Symbol}'; analyzeSymbol();">
                    <span>${l}</span>
                    <span style="color:var(--text-main);font-weight:bold;">${item.Symbol}</span>
                    <span class="prob text-${c === 'bull' ? 'green' : (c === 'base' ? 'blue' : 'yellow')}">Skor: ${scoreValue}</span>
                </div>
                `;
            });
        } else {
            contentBox.innerHTML = `<p style="color:var(--accent-red); text-align:center;">Fırsat bulunamadı veya bir hata oluştu.</p>`;
        }
    } catch (e) {
        contentBox.innerHTML = `<p style="color:var(--accent-red); text-align:center;">Bağlantı hatası: ${e.message}</p>`;
    }
}

async function fetchAKDData(symbol) {
    const loading = document.getElementById('akd-loading');
    const content = document.getElementById('akd-content');
    loading.style.display = 'block';
    content.style.display = 'none';
    
    try {
        const res = await fetch('/api/brokerage/' + symbol);
        const data = await res.json();
        
        if (data.status === 'success') {
            loading.style.display = 'none';
            content.style.display = 'block';
            
            // Populate Buyers
            const bBody = document.getElementById('akd-buyers-tbody');
            bBody.innerHTML = '';
            data.buyers.forEach(b => {
                bBody.innerHTML += `<tr>
                    <td style="font-weight:bold; color:var(--text-main);">${b.broker}</td>
                    <td style="font-family:monospace;">${b.lots.toLocaleString('tr-TR')}</td>
                    <td>%${b.percent}</td>
                    <td style="color:var(--accent-green); font-weight:bold;">₺${b.cost}</td>
                </tr>`;
            });
            bBody.innerHTML += `<tr><td style="color:var(--text-muted);">Diğer</td><td colspan="3" style="color:var(--text-muted); text-align:right;">%${data.buy_other_pct}</td></tr>`;
            
            // Populate Sellers
            const sBody = document.getElementById('akd-sellers-tbody');
            sBody.innerHTML = '';
            data.sellers.forEach(s => {
                sBody.innerHTML += `<tr>
                    <td style="font-weight:bold; color:var(--text-main);">${s.broker}</td>
                    <td style="font-family:monospace;">${s.lots.toLocaleString('tr-TR')}</td>
                    <td>%${s.percent}</td>
                    <td style="color:var(--accent-red); font-weight:bold;">₺${s.cost}</td>
                </tr>`;
            });
            sBody.innerHTML += `<tr><td style="color:var(--text-muted);">Diğer</td><td colspan="3" style="color:var(--text-muted); text-align:right;">%${data.sell_other_pct}</td></tr>`;
            
            // Net Difference
            const netDiffEl = document.getElementById('akd-net-diff');
            if (data.net_diff_lots > 0) {
                netDiffEl.innerHTML = `<span style="color:var(--accent-green);">+${data.net_diff_lots.toLocaleString('tr-TR')} Lot (Para Girişi)</span>`;
            } else if (data.net_diff_lots < 0) {
                netDiffEl.innerHTML = `<span style="color:var(--accent-red);">${data.net_diff_lots.toLocaleString('tr-TR')} Lot (Para Çıkışı)</span>`;
            } else {
                netDiffEl.innerHTML = `<span style="color:var(--text-muted);">Dengeli</span>`;
            }
        } else {
            loading.innerHTML = `<p style="color:var(--accent-red);">Hata: ${data.message}</p>`;
        }
    } catch (e) {
        loading.innerHTML = `<p style="color:var(--accent-red);">Bağlantı Hatası: ${e.message}</p>`;
    }
}

// ========== NEWS ENGINE ==========
async function fetchGlobalNews() {
    const content = document.getElementById('global-news-content');
    content.innerHTML = `<div style="text-align:center; padding: 2rem 0; grid-column: 1 / -1;"><div class="spinner small"></div><p style="margin-top:1rem;color:var(--text-muted)">Haberler RSS kanallarından derleniyor...</p></div>`;
    
    try {
        const res = await fetch('/api/news/global');
        const data = await res.json();
        if (data.status === 'success' && data.news.length > 0) {
            content.innerHTML = "";
            data.news.forEach(item => {
                let card = document.createElement('div');
                card.style.cssText = "background:var(--bg-base); border:1px solid var(--border-color); border-radius:8px; padding:1.5rem; display:flex; flex-direction:column; justify-content:space-between;";
                
                let sourceBadge = `<span style="font-size:0.75rem; background:var(--accent-blue); color:#fff; padding:0.2rem 0.5rem; border-radius:4px; font-weight:bold;">${item.source}</span>`;
                let dateStr = item.published ? `<span style="font-size:0.8rem; color:var(--text-muted);"><i class="fa-regular fa-clock"></i> ${item.published}</span>` : '';
                
                let summary = item.summary.replace(/<[^>]+>/g, '').substring(0, 150) + "...";
                
                card.innerHTML = `
                    <div>
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:1rem;">
                            ${sourceBadge}
                            ${dateStr}
                        </div>
                        <h4 style="margin-bottom:0.5rem; font-size:1.1rem; line-height:1.4;">${item.title}</h4>
                        <p style="color:var(--text-muted); font-size:0.9rem; line-height:1.5; margin-bottom:1rem;">${summary}</p>
                    </div>
                    <a href="${item.link}" target="_blank" style="color:var(--accent-blue); text-decoration:none; font-weight:600; font-size:0.9rem;"><i class="fa-solid fa-arrow-right"></i> Habere Git</a>
                `;
                content.appendChild(card);
            });
        } else {
            content.innerHTML = `<p style="grid-column: 1/-1; color:var(--text-muted);">Güncel haber bulunamadı.</p>`;
        }
    } catch (e) {
        content.innerHTML = `<p style="grid-column: 1/-1; color:var(--accent-red);">Haberler yüklenirken hata oluştu: ${e.message}</p>`;
    }
}

async function fetchTickerNews(symbol) {
    const container = document.getElementById('ticker-news-content');
    container.innerHTML = `<div style="text-align:center;"><div class="spinner small"></div></div>`;
    
    try {
        const res = await fetch('/api/news/ticker/' + symbol);
        const data = await res.json();
        
        if (data.status === 'success' && data.news.length > 0) {
            container.innerHTML = "";
            data.news.forEach(item => {
                let div = document.createElement('div');
                div.style.cssText = "padding:1rem; border:1px solid var(--border-color); border-radius:6px; background:var(--bg-base);";
                let dateStr = item.providerPublishTime ? new Date(item.providerPublishTime * 1000).toLocaleString() : "";
                div.innerHTML = `
                    <div style="font-size:0.8rem; color:var(--text-muted); margin-bottom:0.5rem;">${dateStr} &bull; ${item.publisher}</div>
                    <h4 style="margin-bottom:0.5rem;"><a href="${item.link}" target="_blank" style="color:var(--text-main); text-decoration:none;">${item.title}</a></h4>
                    <a href="${item.link}" target="_blank" style="font-size:0.85rem; color:var(--accent-blue); text-decoration:none;">Detaylar <i class="fa-solid fa-arrow-up-right-from-square"></i></a>
                `;
                container.appendChild(div);
            });
        } else {
            container.innerHTML = `<p style="color:var(--text-muted)">Bu varlığa ait İngilizce kurumsal haber bulunamadı.</p>`;
        }
    } catch (e) {
        container.innerHTML = `<p style="color:var(--accent-red)">Haber servisi hatası: ${e.message}</p>`;
    }
}

// ========== ANALYZE AND DATA BINDING ==========
async function analyzeSymbol() {
    let symbol = symbolInput.value.trim();
    if (!symbol) return;

    if (analysisAbortController) {
        try { analysisAbortController.abort(); } catch(e){}
    }
    analysisAbortController = new AbortController();

    // Switch to dashboard view
    switchMainTab('dashboard', document.querySelectorAll('.nav-btn')[2]);
    document.getElementById('dashboard-wrapper').style.display = 'none';
    document.getElementById('home-wrapper').style.display = 'none';
    document.getElementById('radar-wrapper').style.display = 'none';
    document.getElementById('loading').style.display = 'flex';
    
    // Simulate terminal logs
    simulateTerminalLogs(symbol);

    try {
        const response = await fetch('/api/analyze?symbol=' + encodeURIComponent(symbol), {
            signal: analysisAbortController.signal
        });
        const data = await response.json();

        // Let the logs finish reading
        setTimeout(() => {
            const loadingEl = document.getElementById('loading');
            if (!loadingEl || loadingEl.style.display === 'none') {
                // Analysis was cancelled by user
                return;
            }
            loadingEl.style.display = 'none';
            if (response.status !== 200 || data.status === "error") {
                alert("⛔ UPLINK ERROR\n\n" + (data.message || data.error));
                cancelLoadingAndGoBack();
                return;
            }
            bindDataToDashboard(data.report);
        }, 600);
        
    } catch (error) {
        if (error.name === 'AbortError') {
            console.log('Analiz kullanıcı tarafından iptal edildi.');
            return;
        }
        document.getElementById('loading').style.display = 'none';
        alert("CRITICAL ERROR: Connection lost.\n" + error);
        cancelLoadingAndGoBack();
    }
}

function simulateTerminalLogs(symbol) {
    if (logInterval) clearInterval(logInterval);
    const termLogs = document.getElementById('term-logs');
    termLogs.innerHTML = "";
    const fakeLogs = [
        `> HEDEF KİLİTLENDİ: ${symbol}`,
        "> VERİ SAĞLAYICILARLA GÜVENLİ BAĞLANTI KURULUYOR...",
        "> 10 NOKTALI VERİ DOĞRULAMASI (VALIDATION)... [BAŞARILI]",
        "> VERİLER MOTORLARA (ENGINES) YÖNLENDİRİLİYOR...",
        "> ├─ MAKRO MOTOR: VIX & Piyasa Rejimi Çekiliyor...",
        "> ├─ SMART_MONEY MOTORU: Hacim Anomalileri Hesaplanıyor...",
        "> ├─ TEMEL MOTOR: F/K, PD/DD, Bilanço Değerleniyor...",
        "> └─ TEKNİK MOTOR: RSI, EMA, Trend ve Momentum İşleniyor...",
        "> CIO_AI: KOMİTE TOPLANDI. OYLAMA BAŞLADI...",
        "> RAPOR BAŞARIYLA OLUŞTURULDU VE BÜYÜK BEYİN TARAFINDAN ONAYLANDI."
    ];
    let logIdx = 0;
    logInterval = setInterval(() => {
        if (logIdx < fakeLogs.length) {
            let p = document.createElement('div');
            p.className = 'term-line';
            p.innerText = fakeLogs[logIdx];
            termLogs.appendChild(p);
            termLogs.scrollTop = termLogs.scrollHeight;
            logIdx++;
        } else {
            clearInterval(logInterval);
        }
    }, 100);
}

function safeGet(obj, path, def = "-") {
    return path.split('.').reduce((o, i) => (o ? o[i] : undefined), obj) || def;
}

// Translate UNKNOWN to Turkish
function t(str) {
    if (!str) return "-";
    if (typeof str === 'string') {
        let upperStr = str.toUpperCase();
        if (upperStr === "UNKNOWN") return "Veri Bekleniyor / Nötr";
        if (upperStr === "N/A") return "Bulunamadı (API)";
    }
    return str;
}

let currentChartSymbol = "AKBNK.IS";
let currentChartData = [];
let chartPriceInstance = null;
let chartMacdInstance = null;
let chartRsiInstance = null;

function calculateEMA(data, period) {
    if (data.length === 0) return [];
    const k = 2 / (period + 1);
    let emaArray = [];
    let ema = data[0].y[3];
    emaArray.push({ x: data[0].x, y: ema });
    for (let i = 1; i < data.length; i++) {
        ema = (data[i].y[3] * k) + (ema * (1 - k));
        emaArray.push({ x: data[i].x, y: Number(ema.toFixed(2)) });
    }
    return emaArray;
}

function calculateRSI(data, period=14) {
    if(data.length < period) return [];
    let rsiArray = [];
    let gains = 0, losses = 0;
    
    for(let i=1; i<=period; i++) {
        let diff = data[i].y[3] - data[i-1].y[3];
        if(diff >= 0) gains += diff;
        else losses -= diff;
    }
    let avgGain = gains / period;
    let avgLoss = losses / period;
    
    for(let i=period; i<data.length; i++) {
        if(i > period) {
            let diff = data[i].y[3] - data[i-1].y[3];
            let g = diff >= 0 ? diff : 0;
            let l = diff < 0 ? -diff : 0;
            avgGain = ((avgGain * (period - 1)) + g) / period;
            avgLoss = ((avgLoss * (period - 1)) + l) / period;
        }
        let rs = avgLoss === 0 ? 100 : (avgGain / avgLoss);
        let rsi = avgLoss === 0 ? 100 : (100 - (100 / (1 + rs)));
        rsiArray.push({x: data[i].x, y: Number(rsi.toFixed(2))});
    }
    return rsiArray;
}

function calculateMACD(data, shortP=12, longP=26, sigP=9) {
    let emaShort = calculateEMA(data, shortP);
    let emaLong = calculateEMA(data, longP);
    let macdLine = [];
    
    let startIdx = longP - 1;
    for(let i=startIdx; i<data.length; i++) {
        let macdVal = emaShort[i].y - emaLong[i].y;
        macdLine.push({x: data[i].x, y: macdVal});
    }
    
    let dummyMacd = macdLine.map(m => ({x: m.x, y: [0,0,0,m.y]}));
    let signalEma = calculateEMA(dummyMacd, sigP);
    
    let histogram = [];
    let macdResult = [];
    let signalResult = [];
    
    for(let i=0; i<signalEma.length; i++) {
        let hist = macdLine[i].y - signalEma[i].y;
        macdResult.push({x: macdLine[i].x, y: Number(macdLine[i].y.toFixed(2))});
        signalResult.push({x: signalEma[i].x, y: Number(signalEma[i].y.toFixed(2))});
        histogram.push({x: macdLine[i].x, y: Number(hist.toFixed(2))});
    }
    
    return {macd: macdResult, signal: signalResult, hist: histogram};
}

let lwChart = null;
let lwCandleSeries = null;
let lwVolumeSeries = null;
let lwEma8Series = null;
let lwEma21Series = null;
let lwMacdSeries = null;
let lwMacdSignalSeries = null;
let lwMacdHistSeries = null;

window.currentChartSymbol = '';
window.currentChartInterval = '1d';

window.changeChartInterval = async function(interval) {
    window.currentChartInterval = interval;
    // Update active button
    document.querySelectorAll('.tf-btn').forEach(btn => btn.classList.remove('active'));
    if(event && event.target) event.target.classList.add('active');
    
    await window.renderAdvancedChart();
}

window.renderAdvancedChart = async function() {
    if(!window.currentChartSymbol) return;
    const tvContainer = document.getElementById('tv-chart');
    if (!tvContainer) return;
    tvContainer.innerHTML = '<div style="color:var(--text-muted); padding:20px; text-align:center;">Veri yükleniyor...</div>';
    
    try {
        const response = await fetch(`/api/chart_data?symbol=${window.currentChartSymbol}&interval=${window.currentChartInterval}`);
        const data = await response.json();
        if(data.status !== "success") {
            tvContainer.innerHTML = `<div style="color:red; padding:20px; text-align:center;">Hata: ${data.message}</div>`;
            return;
        }
        tvContainer.innerHTML = ''; // clear loading
        
        // Filter out invalid candles (e.g., Yahoo Finance sometimes returns incomplete current-day bars with NaN/null open/high/low)
        // If we pass null to the CandlestickSeries, it fails silently and the entire pane goes blank.
        if (data.candles) {
            data.candles = data.candles.filter(c => c.open != null && c.high != null && c.low != null && c.close != null);
        }
        
        // Create 6 separate divs for 6 panes
        const div1 = document.createElement('div'); div1.style.flex = '0 0 40%'; div1.style.position = 'relative'; div1.style.minHeight = '250px';
        const div2 = document.createElement('div'); div2.style.flex = '0 0 12%'; div2.style.position = 'relative'; div2.style.minHeight = '80px';
        const div3 = document.createElement('div'); div3.style.flex = '0 0 12%'; div3.style.position = 'relative'; div3.style.minHeight = '80px';
        const div4 = document.createElement('div'); div4.style.flex = '0 0 12%'; div4.style.position = 'relative'; div4.style.minHeight = '80px';
        const div5 = document.createElement('div'); div5.style.flex = '0 0 12%'; div5.style.position = 'relative'; div5.style.minHeight = '80px';
        const div6 = document.createElement('div'); div6.style.flex = '0 0 12%'; div6.style.position = 'relative'; div6.style.minHeight = '80px';
        
        tvContainer.appendChild(div1);
        tvContainer.appendChild(div2);
        tvContainer.appendChild(div3);
        tvContainer.appendChild(div4);
        tvContainer.appendChild(div5);
        tvContainer.appendChild(div6);
        
        const commonOptions = {
            layout: { textColor: '#94A3B8', background: { type: 'solid', color: 'transparent' } },
            grid: { vertLines: { color: 'rgba(255,255,255,0.05)' }, horzLines: { color: 'rgba(255,255,255,0.05)' } },
            crosshair: { mode: LightweightCharts.CrosshairMode.Normal },
            rightPriceScale: { borderColor: '#334155', autoScale: true }
        };
        
        const c1 = LightweightCharts.createChart(div1, { 
            ...commonOptions, 
            timeScale: { visible: false },
            watermark: {
                color: 'rgba(255, 255, 255, 0.04)',
                visible: true,
                text: window.currentChartSymbol || 'RADAR PRO',
                fontSize: 120,
                horzAlign: 'center',
                vertAlign: 'center',
            }
        });
        const c2 = LightweightCharts.createChart(div2, { ...commonOptions, timeScale: { visible: false }});
        const c3 = LightweightCharts.createChart(div3, { ...commonOptions, timeScale: { visible: false }});
        const c4 = LightweightCharts.createChart(div4, { ...commonOptions, timeScale: { visible: false }});
        const c5 = LightweightCharts.createChart(div5, { ...commonOptions, timeScale: { visible: false }});
        const c6 = LightweightCharts.createChart(div6, { ...commonOptions, timeScale: { timeVisible: true, secondsVisible: false, borderColor: '#334155' }});
        
        window.lwChart = c1; // Keep reference to main chart for backward compat
        
        if (window.chartResizeObserver) {
            window.chartResizeObserver.disconnect();
        }
        
        window.chartResizeObserver = new ResizeObserver(entries => {
            if (entries.length === 0 || entries[0].target !== tvContainer) return;
            const width = entries[0].contentRect.width;
            c1.applyOptions({ width: width, height: div1.clientHeight });
            c2.applyOptions({ width: width, height: div2.clientHeight });
            c3.applyOptions({ width: width, height: div3.clientHeight });
            c4.applyOptions({ width: width, height: div4.clientHeight });
            c5.applyOptions({ width: width, height: div5.clientHeight });
            c6.applyOptions({ width: width, height: div6.clientHeight });
        });
        window.chartResizeObserver.observe(tvContainer);
        
        // PANE 1: Price, EMA, Volume
        c1.priceScale('right').applyOptions({ scaleMargins: { top: 0.05, bottom: 0.15 } });
        let sCandle = c1.addCandlestickSeries({ upColor: '#10B981', downColor: '#EF4444', borderVisible: false, wickUpColor: '#10B981', wickDownColor: '#EF4444' });
        sCandle.setData(data.candles);
        sCandle.setMarkers(data.annotations);
        
        // Draw Support and Resistance Lines
        if (data.pivots) {
            const drawLevel = (price, color, title) => {
                sCandle.createPriceLine({
                    price: price,
                    color: color,
                    lineWidth: 1,
                    lineStyle: LightweightCharts.LineStyle.Dashed,
                    axisLabelVisible: true,
                    title: title,
                });
            };
            drawLevel(data.pivots.R3, 'rgba(239, 68, 68, 0.7)', 'R3');
            drawLevel(data.pivots.R2, 'rgba(239, 68, 68, 0.7)', 'R2');
            drawLevel(data.pivots.R1, 'rgba(248, 113, 113, 0.7)', 'R1');
            drawLevel(data.pivots.P, 'rgba(148, 163, 184, 0.7)', 'Pivot');
            drawLevel(data.pivots.S1, 'rgba(74, 222, 128, 0.7)', 'S1');
            drawLevel(data.pivots.S2, 'rgba(16, 185, 129, 0.7)', 'S2');
            drawLevel(data.pivots.S3, 'rgba(5, 150, 105, 0.7)', 'S3');
        }
        
        let sVol = c1.addHistogramSeries({ color: '#64748b', priceFormat: { type: 'volume' }, priceScaleId: '' });
        c1.priceScale('').applyOptions({
            scaleMargins: {
                top: 0.8,
                bottom: 0,
            },
        });
        sVol.setData(data.candles.map(c => ({ time: c.time, value: c.volume, color: c.close > c.open ? 'rgba(16, 185, 129, 0.4)' : 'rgba(239, 68, 68, 0.4)' })));
        
        let sEma8 = c1.addLineSeries({ color: '#3b82f6', lineWidth: 1 });
        sEma8.setData(data.candles.map(c => c.ema8 != null ? {time: c.time, value: c.ema8} : {time: c.time}));
        let sEma21 = c1.addLineSeries({ color: '#f59e0b', lineWidth: 1 });
        sEma21.setData(data.candles.map(c => c.ema21 != null ? {time: c.time, value: c.ema21} : {time: c.time}));
        
        // PANE 2: MACD

        c2.priceScale('right').applyOptions({ scaleMargins: { top: 0.1, bottom: 0.1 } });
        let sMacd = c2.addLineSeries({ color: '#3b82f6', lineWidth: 1.5 });
        sMacd.setData(data.candles.map(c => c.macd != null ? {time: c.time, value: c.macd} : {time: c.time}));
        let sMacdSig = c2.addLineSeries({ color: '#f59e0b', lineWidth: 1.5 });
        sMacdSig.setData(data.candles.map(c => c.macd_signal != null ? {time: c.time, value: c.macd_signal} : {time: c.time}));
        let sMacdHist = c2.addHistogramSeries({});
        sMacdHist.setData(data.candles.map(c => c.macd_hist != null ? {time: c.time, value: c.macd_hist, color: c.macd_hist >= 0 ? 'rgba(16, 185, 129, 0.6)' : 'rgba(239, 68, 68, 0.6)'} : {time: c.time}));
        
        // PANE 3: RSI
        c3.priceScale('right').applyOptions({ scaleMargins: { top: 0.1, bottom: 0.1 } });
        let sRsi = c3.addBaselineSeries({ 
            baseValue: { type: 'price', price: 50 }, 
            topLineColor: '#10B981', 
            topFillColor1: 'rgba(16, 185, 129, 0.4)', 
            topFillColor2: 'rgba(16, 185, 129, 0.05)', 
            bottomLineColor: '#EF4444', 
            bottomFillColor1: 'rgba(239, 68, 68, 0.05)', 
            bottomFillColor2: 'rgba(239, 68, 68, 0.4)', 
            lineWidth: 2 
        });
        sRsi.setData(data.candles.map(c => c.rsi != null ? {time: c.time, value: c.rsi} : {time: c.time}));
        // RSI 70, 50, and 30 Reference Lines
        sRsi.createPriceLine({ price: 70, color: 'rgba(239, 68, 68, 0.5)', lineWidth: 1, lineStyle: 2, title: '70', axisLabelVisible: true });
        sRsi.createPriceLine({ price: 50, color: 'rgba(148, 163, 184, 0.5)', lineWidth: 1, lineStyle: 2, title: '50', axisLabelVisible: true });
        sRsi.createPriceLine({ price: 30, color: 'rgba(16, 185, 129, 0.5)', lineWidth: 1, lineStyle: 2, title: '30', axisLabelVisible: true });

        // PANE 4: ADX
        c4.priceScale('right').applyOptions({ scaleMargins: { top: 0.1, bottom: 0.1 } });
        
        let sAdx = c4.addLineSeries({ lineWidth: 2 });
        sAdx.setData(data.candles.map(c => {
            if (c.adx === null) return {time: c.time};
            let color = '#93c5fd'; // 0-20 (Açık Mavi / Trend Yok)
            if (c.adx >= 20 && c.adx < 25) color = '#60a5fa'; // 20-25 (Trend Başlangıcı)
            else if (c.adx >= 25 && c.adx < 50) color = '#3b82f6'; // 25-50 (Güçlü Trend)
            else if (c.adx >= 50 && c.adx < 75) color = '#2563eb'; // 50-75 (Çok Güçlü)
            else if (c.adx >= 75) color = '#1e3a8a'; // 75-100 (Aşırı Güçlü / Koyu Mavi)
            return { time: c.time, value: c.adx, color: color };
        }));
        sAdx.createPriceLine({ price: 25, color: '#10B981', lineWidth: 2, lineStyle: 2, title: '25', axisLabelVisible: true });
        
        let sAdxArea = c4.addAreaSeries({ lineColor: 'transparent', topColor: 'rgba(239, 68, 68, 0.3)', bottomColor: 'rgba(239, 68, 68, 0.05)' });
        sAdxArea.setData(data.candles.map(c => c.adx != null ? {time: c.time, value: c.plus_di > c.minus_di ? c.adx : 0} : {time: c.time}));

        // PANE 5: Momentum
        c5.priceScale('right').applyOptions({ visible: true, scaleMargins: { top: 0.1, bottom: 0.1 } });
        let sMom = c5.addHistogramSeries({ priceScaleId: 'right', base: 0 });
        sMom.setData(data.candles.map(c => c.momentum != null ? {
            time: c.time, 
            value: c.momentum, 
            color: c.momentum >= 0 ? 'rgba(16, 185, 129, 0.6)' : 'rgba(239, 68, 68, 0.6)'
        } : {time: c.time}));
        
        // PANE 6: BB %B & ATR
        c6.priceScale('right').applyOptions({ scaleMargins: { top: 0.1, bottom: 0.1 } });
        c6.priceScale('left').applyOptions({ visible: true, scaleMargins: { top: 0.1, bottom: 0.1 } });
        
        let sBb = c6.addBaselineSeries({ 
            baseValue: { type: 'price', price: 0.5 }, 
            topLineColor: '#10B981', 
            topFillColor1: 'rgba(16, 185, 129, 0.4)', 
            topFillColor2: 'rgba(16, 185, 129, 0.05)', 
            bottomLineColor: '#EF4444', 
            bottomFillColor1: 'rgba(239, 68, 68, 0.05)', 
            bottomFillColor2: 'rgba(239, 68, 68, 0.4)', 
            lineWidth: 2 
        });
        sBb.setData(data.candles.map(c => c.bb_pb != null ? {time: c.time, value: c.bb_pb} : {time: c.time}));
        
        let sAtr = c6.addLineSeries({ priceScaleId: 'left', color: '#8b5cf6', lineWidth: 1.5 });
        sAtr.setData(data.candles.map(c => c.atr != null ? {time: c.time, value: c.atr} : {time: c.time}));
        
        // Sync TimeScale using LogicalRange to avoid zooming feedback loops at the edges
        const charts = [c1, c2, c3, c4, c5, c6];
        let isSyncing = false;
        charts.forEach(source => {
            source.timeScale().subscribeVisibleLogicalRangeChange(range => {
                if (isSyncing || !range) return;
                isSyncing = true;
                charts.forEach(target => {
                    if (source !== target) target.timeScale().setVisibleLogicalRange(range);
                });
                isSyncing = false;
            });
        });
        // Crosshair Sync & Tooltip Logic
        const tooltip = document.getElementById('chart-tooltip');
        const ttDate = document.getElementById('tt-date');
        const ttO = document.getElementById('tt-o');
        const ttH = document.getElementById('tt-h');
        const ttL = document.getElementById('tt-l');
        const ttC = document.getElementById('tt-c');
        const ttVol = document.getElementById('tt-vol');
        
        const syncCrosshair = (param, sourceChart) => {
            if (!param.time || param.point.x < 0 || param.point.y < 0) {
                tooltip.style.display = 'none';
                charts.forEach(c => { if (c !== sourceChart) c.clearCrosshairPosition(); });
                return;
            }
            
            // 1. Sync Crosshairs
            charts.forEach(c => {
                if (c !== sourceChart) {
                    // Try to set crosshair on the first series of the target chart to get vertical line
                    let targetSeries = null;
                    if (c === c1) targetSeries = sCandle;
                    else if (c === c2) targetSeries = sMacd;
                    else if (c === c3) targetSeries = sRsi;
                    else if (c === c4) targetSeries = sAdx;
                    else if (c === c5) targetSeries = sMom;
                    else if (c === c6) targetSeries = sBb;
                    
                    if (targetSeries) {
                        let crosshairPrice = 0;
                        // Find the matching data point to use its real price so we don't break auto-scaling
                        const pointData = data.candles.find(d => d.time === param.time);
                        if (pointData) {
                            if (c === c1) crosshairPrice = pointData.close;
                            else if (c === c2) crosshairPrice = pointData.macd || 0;
                            else if (c === c3) crosshairPrice = pointData.rsi || 50;
                            else if (c === c4) crosshairPrice = pointData.adx || 20;
                            else if (c === c5) crosshairPrice = pointData.momentum || 0;
                            else if (c === c6) crosshairPrice = pointData.bb_pb || 0.5;
                        }
                        c.setCrosshairPosition(crosshairPrice, param.time, targetSeries);
                    }
                }
            });
            
            // 2. Update Tooltip
            tooltip.style.display = 'block';
            
            // Try to find candle data for this time
            const candleData = param.seriesData.get(sCandle);
            if (candleData && candleData.open !== undefined) {
                let dateStr = "";
                if (typeof param.time === 'string') {
                    dateStr = param.time;
                } else {
                    const dt = new Date(param.time * 1000);
                    dateStr = dt.toLocaleString('tr-TR');
                }
                ttDate.textContent = dateStr;
                ttO.textContent = candleData.open.toFixed(2);
                ttH.textContent = candleData.high.toFixed(2);
                ttL.textContent = candleData.low.toFixed(2);
                ttC.textContent = candleData.close.toFixed(2);
                
                // Color formatting
                ttC.style.color = candleData.close >= candleData.open ? '#10b981' : '#ef4444';
            }
            
            const volData = param.seriesData.get(sVol);
            if (volData) {
                ttVol.textContent = 'Hacim: ' + (volData.value / 1000000).toFixed(2) + 'M';
            }
        };

        charts.forEach(c => {
            c.subscribeCrosshairMove(param => syncCrosshair(param, c));
        });

        // Save to global state
        window.globalCharts = charts;
        window.globalChartData = data.candles;
        window.globalSeries = {
            pane1: { sEma8, sEma21 },
            pane2: { sMacd, sMacdSig, sMacdHist },
            pane3: { sRsi },
            pane4: { sAdx, sAdxArea },
            pane5: { sMom },
            pane6: { sBb, sAtr }
        };
        
        // Settings Modal Handlers
        [div1, div2, div3, div4, div5, div6].forEach((div, index) => {
            div.addEventListener('dblclick', (e) => {
                e.preventDefault();
                openIndicatorSettings(`pane${index + 1}`);
            });
        });
        
    } catch (err) {
        console.error(err);
        tvContainer.innerHTML = `<div style="color:red; padding:20px; text-align:center;">Bir hata oluştu: ${err.message}</div>`;
    }
} // <--- Added missing brace for renderAdvancedChart

function loadCustomChart(sym) {
    window.currentChartSymbol = sym;
    window.currentChartInterval = '1d';
    document.querySelectorAll('.tf-btn').forEach(btn => btn.classList.remove('active'));
    const btn = Array.from(document.querySelectorAll('.tf-btn')).find(b => b.getAttribute('onclick') === "changeChartInterval('1d')");
    if(btn) btn.classList.add('active');
    
    window.renderAdvancedChart();
}

// ========== DYNAMIC CHART SETTINGS ==========
function openIndicatorSettings(paneId) {
    const seriesMap = window.globalSeries[paneId];
    if (!seriesMap) return;
    
    const modal = document.getElementById('indicator-modal');
    const list = document.getElementById('modal-indicators-list');
    list.innerHTML = ''; // clear
    
    Object.keys(seriesMap).forEach(key => {
        const ser = seriesMap[key];
        const row = document.createElement('div');
        row.style.display = 'flex';
        row.style.alignItems = 'center';
        row.style.gap = '10px';
        row.style.background = 'rgba(0,0,0,0.2)';
        row.style.padding = '8px';
        row.style.borderRadius = '4px';
        
        row.innerHTML = `
            <div style="flex:1; color:#94a3b8; font-weight:bold; font-size:0.9rem;">${key}</div>
            <input type="color" id="col-${key}" value="#3b82f6" style="width:30px; height:30px; border:none; cursor:pointer; background:transparent;">
            <input type="range" id="opc-${key}" min="0.1" max="1" step="0.1" value="1" style="width:70px;">
            <input type="number" id="wid-${key}" min="1" max="5" value="1" style="width:40px; background:#0f172a; color:#fff; border:1px solid #334155;">
            <button onclick="updateIndicatorStyle('${paneId}', '${key}')" style="background:var(--accent-blue); color:#fff; border:none; padding:4px 8px; border-radius:4px; cursor:pointer; font-size:0.8rem;">Uygula</button>
        `;
        list.appendChild(row);
    });
    
    modal.style.display = 'block';
}

window.updateIndicatorStyle = function(paneId, seriesKey) {
    const ser = window.globalSeries[paneId][seriesKey];
    if (!ser) return;
    
    const hex = document.getElementById(`col-${seriesKey}`).value;
    const opacity = document.getElementById(`opc-${seriesKey}`).value;
    const width = parseInt(document.getElementById(`wid-${seriesKey}`).value);
    
    let r = parseInt(hex.slice(1, 3), 16),
        g = parseInt(hex.slice(3, 5), 16),
        b = parseInt(hex.slice(5, 7), 16);
    const rgba = `rgba(${r}, ${g}, ${b}, ${opacity})`;
    
    try {
        ser.applyOptions({
            color: rgba,
            lineColor: rgba,
            topColor: rgba,
            bottomColor: `rgba(${r}, ${g}, ${b}, 0.05)`,
            lineWidth: width
        });
    } catch(e) {
        console.error("Could not apply styles to", seriesKey, e);
    }
}

function bindDataToDashboard(report) {
    document.getElementById('dashboard-wrapper').style.display = 'block';

    // 1. TICKER HEADER
    const sym = safeGet(report, "META.Symbol", "-");
    document.title = t(sym) + " | COMMAND CENTER";
    setElText('tk-sym', t(sym));
    
    let cp = safeGet(report, "META.Current_Price", "0.00");
    let c_pct = safeGet(report, "META.Change_Pct", undefined);
    
    // JS Fallback for Change_Pct if backend hasn't restarted
    if (c_pct === undefined) {
        let ohlcData = safeGet(report, "Section_32_Historical_Data", []);
        if (ohlcData && ohlcData.length >= 2) {
            let last = ohlcData[ohlcData.length - 1];
            let prev = ohlcData[ohlcData.length - 2];
            if (prev.close > 0) {
                c_pct = ((last.close - prev.close) / prev.close) * 100;
            }
        }
    }

    let tkPriceHtml = cp + " TRY";
    if (c_pct !== undefined) {
        let p_pct = parseFloat(c_pct);
        let p_c = p_pct > 0 ? "var(--accent-green)" : (p_pct < 0 ? "var(--accent-red)" : "var(--text-muted)");
        let p_sign = p_pct > 0 ? "+" : "";
        tkPriceHtml += ` <span style="color:${p_c}; font-size:1.2rem; font-weight:500;">(${p_sign}%${p_pct.toFixed(2)})</span>`;
    }
    const tkPriceEl = document.getElementById('tk-price');
    if (tkPriceEl) tkPriceEl.innerHTML = tkPriceHtml;

    setElText('tk-time', safeGet(report, "META.Timestamp", ""));
    setElText('ig-val', t(safeGet(report, "Section_2_Grade", "N/A")));
    setElText('score-regime', t(safeGet(report, "Section_7_Regime", "-")));

    // CHART SYSTEM: LOAD CUSTOM CHART (APEX WITH EMA)
    currentChartSymbol = sym;
    loadCustomChart(sym, safeGet(report, "Section_32_Historical_Data", []));
    
    // FETCH TICKER NEWS
    fetchTickerNews(sym);

    // 2. OVERVIEW TAB
    let conf = parseFloat(safeGet(report, "Section_4_Confidence", 0));
    let risk = parseFloat(safeGet(report, "Section_5_Risk", 0));
    drawScoreChart(conf, risk);

    // 0. CONVICTION & ACTION PLAYBOOK (BAŞ YATIRIM YÖNETİCİSİ İKNA RAPORU)
    const playbook = safeGet(report, "Section_0_Conviction_Playbook", null);
    const convWrapper = document.getElementById('conviction-wrapper');
    if (convWrapper) {
        if (playbook) {
            convWrapper.style.display = 'block';
            convWrapper.style.borderColor = playbook.Verdict_Color || 'var(--accent-green)';
            setElText('conviction-title', playbook.Verdict_Title || 'CIO KURUMSAL KARAR RAPORU');
            setElText('conviction-rr-val', playbook.Risk_Reward_Ratio || '1 : 2.5');
            
            const actionBadge = document.getElementById('conviction-action-badge');
            if (actionBadge) {
                actionBadge.textContent = playbook.Verdict_Badge || 'GÜÇLÜ AL';
                actionBadge.style.background = playbook.Verdict_Color || 'var(--accent-green)';
                actionBadge.style.color = '#000';
            }
            
            const pitchEl = document.getElementById('conviction-pitch');
            if (pitchEl) {
                pitchEl.innerHTML = playbook.Executive_Pitch || '';
                pitchEl.style.borderLeftColor = playbook.Verdict_Color || 'var(--accent-green)';
            }
            
            const proofsUl = document.getElementById('conviction-proofs');
            if (proofsUl) {
                proofsUl.innerHTML = '';
                (playbook.Top_3_Proofs || []).forEach(p => {
                    proofsUl.innerHTML += `<li style="background: rgba(0,0,0,0.2); padding: 8px 12px; border-radius: 6px; border-left: 3px solid var(--accent-yellow);">${p}</li>`;
                });
            }
            
            const stepsUl = document.getElementById('conviction-steps');
            if (stepsUl) {
                stepsUl.innerHTML = '';
                (playbook.Tactical_Steps || []).forEach(s => {
                    stepsUl.innerHTML += `<li style="background: rgba(0,0,0,0.2); padding: 8px 12px; border-radius: 6px; border-left: 3px solid var(--accent-green);">${s}</li>`;
                });
            }
            
            const warrantText = document.getElementById('conviction-warrant-text');
            if (warrantText) {
                warrantText.innerHTML = playbook.Warrant_Tactics || '⚡ Varant bilgisi hesaplanamadı.';
            }
        } else {
            let fallbackConf = parseFloat(safeGet(report, "Section_4_Confidence", 50));
            let fallbackBadge = fallbackConf >= 70 ? "GÜÇLÜ AL" : (fallbackConf >= 50 ? "KADEMELİ AL" : "İZLE / BEKLE");
            let fallbackColor = fallbackConf >= 70 ? "var(--accent-green)" : (fallbackConf >= 50 ? "var(--accent-blue)" : "var(--accent-yellow)");
            setElText('conviction-title', `🚨 ${sym} İÇİN YAPAY ZEKA VE CIO KARAR RAPORU`);
            setElText('conviction-rr-val', "1 : 3.0");
            const actionBadge = document.getElementById('conviction-action-badge');
            if (actionBadge) {
                actionBadge.textContent = fallbackBadge;
                actionBadge.style.background = fallbackColor;
                actionBadge.style.color = '#000';
            }
            const pitchEl = document.getElementById('conviction-pitch');
            if (pitchEl) {
                pitchEl.innerHTML = safeGet(report, "Section_1_Executive", "Analiz verisi inceleniyor.");
                pitchEl.style.borderLeftColor = fallbackColor;
            }
        }
    }

    setElText('pos-amt', safeGet(report, "Section_9_Position.Amount"));
    setElText('pos-scale', safeGet(report, "Section_9_Position.Scaling"));
    setElText('pos-e1', safeGet(report, "Section_9_Position.Entry_1"));
    setElText('pos-e2', safeGet(report, "Section_9_Position.Entry_2"));
    
    // Get Stop Loss value from Operations Exit Plan
    setElText('pos-sl', "₺" + safeGet(report, "Section_24_Operations.Exit.Stop_Loss_2", "-")); 

    setElText('ex-tp1', safeGet(report, "Section_10_Exit.TP1"));
    setElText('ex-tp2', safeGet(report, "Section_10_Exit.TP2"));
    setElText('ex-strat', safeGet(report, "Section_10_Exit.Strategy"));

    setElText('exec-sum', safeGet(report, "Section_1_Executive"));

    setElText('ai-narrative', safeGet(report, "Section_34_AINarrative", "Analiz bulunamadı."));
    
    // Bind Historical News
    const historicalNews = safeGet(report, "Section_33_HistoricalNews", []);
    const newsContainer = document.getElementById('historical-news-container');
    if (newsContainer) {
        newsContainer.innerHTML = '';
        if (historicalNews && historicalNews.length > 0) {
            historicalNews.forEach(news => {
                let sentColor = "var(--text-muted)";
                if (news.sentiment > 0.3) sentColor = "var(--accent-green)";
                else if (news.sentiment < -0.3) sentColor = "var(--accent-red)";
                
                newsContainer.innerHTML += `
                    <div style="border-bottom:1px solid rgba(255,255,255,0.05); padding-bottom:10px; margin-bottom:10px;">
                        <div style="font-size:0.75rem; color:var(--text-muted); margin-bottom:5px;">${news.published} | ${news.publisher} <span style="float:right; color:${sentColor}">● Duygu Skoru: ${news.sentiment.toFixed(2)}</span></div>
                        <a href="${news.url}" target="_blank" style="color:var(--text-main); font-weight:600; text-decoration:none; font-size:0.9rem;">${news.title}</a>
                    </div>
                `;
            });
        } else {
            newsContainer.innerHTML = '<div class="text-muted text-center py-3">Geçmiş haber verisi bulunamadı.</div>';
        }
    }
    // Operational Data
    setElText('op-pyramid', safeGet(report, "Section_20_CIO_Executive_Summary.Pyramiding", "-"));
    setElText('op-short', safeGet(report, "Section_20_CIO_Executive_Summary.Short_Term_Advice", "-"));
    setElText('op-long', safeGet(report, "Section_20_CIO_Executive_Summary.Long_Term_Advice", "-"));

    // NEW: Render AI Committee Votes
    const committeeVotes = safeGet(report, "Section_19_Reasoning.Committee_Votes", null);
    const cContainer = document.getElementById('committee-container');
    if (cContainer) {
        cContainer.innerHTML = "";
        if (committeeVotes && Object.keys(committeeVotes).length > 0) {
            for (const [aiName, aiData] of Object.entries(committeeVotes)) {
                let voteColor = "var(--text-main)";
                let icon = "fa-robot";
                if (aiData.Vote === "AL" || aiData.Vote === "BUY") { voteColor = "var(--accent-green)"; icon = "fa-arrow-trend-up"; }
                else if (aiData.Vote === "SAT" || aiData.Vote === "SELL") { voteColor = "var(--accent-red)"; icon = "fa-arrow-trend-down"; }
                else if (aiData.Vote === "BEKLE" || aiData.Vote === "NO_TRADE") { voteColor = "var(--accent-yellow)"; icon = "fa-hand"; }
                
                let weight = aiData.Weight_Pct ? parseFloat(aiData.Weight_Pct).toFixed(0) : "25";
                let winRate = aiData.Win_Rate ? parseFloat(aiData.Win_Rate).toFixed(1) : "N/A";
                let totalTrades = aiData.Total_Trades || 0;
                
                let prettyName = aiName.replace("_AI", " Zekası");
                if(aiName === "Technical_AI") prettyName = "Teknik Analiz Ajanı";
                if(aiName === "Fundamental_AI") prettyName = "Temel Analiz (Bilanço) Ajanı";
                if(aiName === "Macro_AI") prettyName = "Makro (Rejim) Ajanı";
                if(aiName === "SmartMoney_AI") prettyName = "Akıllı Para Ajanı";
                
                // Başarı oranını başlığa ekle
                prettyName = `${prettyName} (%${winRate})`;

                let historyHtml = "";
                if (aiData.History && aiData.History.length >= 2) {
                    let last = aiData.History[aiData.History.length - 1];
                    let prev = aiData.History[aiData.History.length - 2];
                    if (last > prev) {
                        historyHtml = `<span style="color:var(--accent-green); font-size:0.7rem; margin-left:5px;"><i class="fa-solid fa-arrow-up"></i> Gelişiyor</span>`;
                    } else if (last < prev) {
                        historyHtml = `<span style="color:var(--accent-red); font-size:0.7rem; margin-left:5px;"><i class="fa-solid fa-arrow-down"></i> Geriliyor</span>`;
                    } else {
                        historyHtml = `<span style="color:var(--text-muted); font-size:0.7rem; margin-left:5px;"><i class="fa-solid fa-minus"></i> Stabil</span>`;
                    }
                }
                
                const cardHtml = `
                    <div style="background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.05); padding: 1rem; border-radius: 8px; margin-bottom: 0.5rem;">
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 0.5rem;">
                            <strong style="color:var(--text-light);"><i class="fa-solid ${icon}" style="color:${voteColor}; margin-right:5px;"></i> ${prettyName}</strong>
                            <span style="background:${voteColor}20; color:${voteColor}; padding:2px 8px; border-radius:4px; font-weight:bold; font-size:0.8rem;">${aiData.Vote}</span>
                        </div>
                        <div style="font-size:0.8rem; color:var(--text-muted); margin-bottom: 0.8rem; min-height:35px;">
                            ${aiData.Reasoning || "-"}
                        </div>
                        <div style="display:flex; justify-content:space-between; font-size:0.85rem;">
                            <div>
                                <div style="color:var(--text-muted); font-size:0.7rem;">GÜNCEL AĞIRLIK</div>
                                <strong style="color:var(--accent-blue);">%${weight}</strong>
                            </div>
                            <div style="text-align:right;">
                                <div style="color:var(--text-muted); font-size:0.7rem;">BAŞARI ORANI (${totalTrades} İşlem)</div>
                                <strong style="color:${winRate > 65 ? 'var(--accent-green)' : 'var(--accent-yellow)'};">%${winRate}</strong>${historyHtml}
                            </div>
                        </div>
                        <div style="width:100%; background:var(--bg-darker); height:4px; border-radius:2px; margin-top:5px; overflow:hidden;">
                            <div style="width:${winRate}%; background: ${winRate > 65 ? 'var(--accent-green)' : 'var(--accent-yellow)'}; height:100%;"></div>
                        </div>
                    </div>
                `;
                cContainer.innerHTML += cardHtml;
            }
        } else {
            cContainer.innerHTML = `<div style="grid-column: span 2; text-align:center; color:var(--text-muted);">Yapay Zeka Komite verisi bulunamadı.</div>`;
        }
    }

    const ulDos = document.getElementById('list-dos');
    ulDos.innerHTML = "";
    (safeGet(report, "Section_11_Do", []) || []).forEach(item => {
        let li = document.createElement('li'); li.innerText = item; ulDos.appendChild(li);
    });

    const ulDonts = document.getElementById('list-donts');
    ulDonts.innerHTML = "";
    (safeGet(report, "Section_12_Dont", []) || []).forEach(item => {
        let li = document.createElement('li'); li.innerText = item; ulDonts.appendChild(li);
    });

    // 3. TECHNICAL TAB
    
    // UYUYAN DEVLER FAZ 1 (ORDER FLOW & SMART MONEY)
    const orderFlow = safeGet(report, "Section_25_OrderFlow", {});
    const smartMoneyDeep = safeGet(report, "Section_26_SmartMoney", {});
    const fundamental = safeGet(report, "Section_27_Fundamental", {});
    const sentiment = safeGet(report, "Section_28_Sentiment", {});
    
    // Fundamental (Bilanço)
    setElText('fun-pe', fundamental.P_E_Ratio || "N/A");
    setElText('fun-roe', fundamental.ROE || "N/A");
    setElText('fun-debt', fundamental.Debt_to_Equity || "N/A");
    setElText('fun-score', fundamental.Score !== undefined ? parseFloat(fundamental.Score).toFixed(1) : "-");
    
    // Sentiment (Duygu Analizi)
    setElText('sen-count', sentiment.News_Count !== undefined ? sentiment.News_Count + " Haber" : "-");
    setElText('sen-status', sentiment.Status || "-");
    setElText('sen-score', sentiment.Score !== undefined ? parseFloat(sentiment.Score).toFixed(1) : "-");
    setElText('sen-analysis', sentiment.Analysis || "-");

    // Smart Money Data
    setElText('of-pressure', orderFlow.Buyer_Pressure || "-");
    window.showLiquidityPopup = function() {
        Swal.fire({
            title: 'Likidite Avı (Stop Patlatma)',
            icon: 'info',
            html: `
                <div style="text-align:left; font-size:0.95rem; line-height:1.6;">
                <b>Büyük Oyuncuların (Balinalar) Tuzağı:</b><br><br>
                Küçük yatırımcılar hisse alırken zararı durdurmak için desteklerin hemen altına "Stop-Loss" emri koyarlar.<br><br>
                Büyük fonlar yüklü mal toplamak istediklerinde, fiyatı bilerek bu desteklerin altına iterek küçük yatırımcının stoplarını <b>patlatır</b> ve panik satışı başlatır.<br><br>
                Ortaya çıkan bu ucuz hisse havuzunu en dipten toplayan büyük oyuncu, ardından fiyatı hızla yukarı çeker (V Dönüşü).<br><br>
                <span style="color:var(--accent-green); font-weight:bold;">Sistem Neden Uyardı?</span><br>
                Grafikte aşağı yönlü sert bir iğne ve peşinden gelen yüksek hacimli toparlanma tespit edildi. Düşüş sahteydi. Büyük para girişi var, <b>güçlü bir AL sinyali</b> olabilir.
                </div>
            `,
            confirmButtonText: 'Anladım',
            background: 'var(--bg-base)',
            color: 'var(--text-main)',
            customClass: { popup: 'glass-panel', confirmButton: 'btn-primary' }
        });
    };

    let sweepText = orderFlow.Liquidity_Sweeps || "-";
    if (sweepText.includes("LİKİDİTE") || sweepText.includes("Likidite") || sweepText.includes("STOP")) {
        document.getElementById('of-sweep').innerHTML = `<span style="color:var(--accent-yellow); font-weight:bold; cursor:pointer; border-bottom:1px dashed var(--accent-yellow);" onclick="showLiquidityPopup()">${sweepText} <i class="fa-solid fa-circle-info"></i></span>`;
    } else {
        setElText('of-sweep', sweepText);
    }
    setElText('of-imbalance', orderFlow.Imbalance_Score ? parseFloat(orderFlow.Imbalance_Score).toFixed(2) : "-");
    
    setElText('sm-action', smartMoneyDeep.Whale_Action || "-");
    setElText('sm-obv', smartMoneyDeep.OBV_Trend || "-");
    setElText('sm-mfi', smartMoneyDeep.MFI ? parseFloat(smartMoneyDeep.MFI).toFixed(1) : "-");

    // FAZ 3: RELIABILITY & OPTIONS (VARANT)
    const reliability = safeGet(report, "Section_18_Reliability", {});
    const options = safeGet(report, "Section_29_Options", {});

    setElText('bt-cases', reliability.Analogues ? reliability.Analogues + " Gün" : "-");
    setElText('bt-hitrate', reliability.Hit_Rate || "-");
    setElText('mc-risk', reliability.Monte_Carlo_Risk || "-");
    
    // Average_Days_to_Target might be in Reliability if we put it there, wait, did I put it there?
    // Let's check executive.py later, but for now we'll safely try to get it.
    setElText('bt-days', reliability.Average_Days_to_Target ? reliability.Average_Days_to_Target + " Gün" : "-");

    setElText('op-iv', options.Implied_Volatility || "-");
    setElText('op-theta', options.Theta_Risk || "-");
    setElText('op-suit', options.Leverage_Suitability || "-");
    setElText('op-score', options.Score !== undefined ? parseFloat(options.Score).toFixed(1) : "-");
    
    const ops = safeGet(report, "Section_24_Operations", {});
    const entry = ops.Entry || {};
    const exit = ops.Exit || {};
    const sup = ops.Support || {};
    const res = ops.Resistance || {};
    
    // AVERAGE COST AND EXITS
    setElText('pos-avg', entry.Average_Cost || "-");
    const dashAtrEl = document.getElementById('op-atr') || document.getElementById('dash-atr');
    if (dashAtrEl) {
        dashAtrEl.textContent = ops.Dynamic_ATR ? "₺" + ops.Dynamic_ATR : "-";
    }
    
    // Bind SVR Projections
    const projections = safeGet(report, "Section_31_Projections", null);
    bindSvrProjections(projections);
    
    setElText('ent-1', entry.Entry_1 || "-");
    setElText('ent-2', entry.Entry_2 || "-");
    setElText('ent-3', entry.Entry_3 || "-");
    setElText('ent-avg', entry.Average_Cost || "-");
    
    setElText('tp-1', exit.Take_Profit_1 || "-");
    setElText('tp-2', exit.Take_Profit_2 || "-");
    setElText('tp-3', exit.Take_Profit_3 || "-");
    
    setElText('sl-1', exit.Stop_Loss_1 || "-");
    setElText('sl-2', exit.Stop_Loss_2 || "-");
    setElText('sl-3', exit.Stop_Loss_3 || "-");
    
    setElText('sup-s1', sup.S1 || "-");
    setElText('sup-s2', sup.S2 || "-");
    setElText('sup-s3', sup.S3 || "-");
    setElText('sup-sub1', sup.Sub_S1 || "-");
    setElText('sup-sub2', sup.Sub_S2 || "-");
    setElText('sup-sub3', sup.Sub_S3 || "-");
    
    setElText('res-r1', res.R1 || "-");
    setElText('res-r2', res.R2 || "-");
    setElText('res-r3', res.R3 || "-");
    setElText('res-sup1', res.Sup_R1 || "-");
    setElText('res-sup2', res.Sup_R2 || "-");
    setElText('res-sup3', res.Sup_R3 || "-");
    
    const mtf = safeGet(report, "Section_30_MTF_Indicators", {});
    const mtfBody = document.getElementById('mtf-body');
    mtfBody.innerHTML = "";
    if (Object.keys(mtf).length > 0) {
        for (const [period, data] of Object.entries(mtf)) {
            const tr = document.createElement('tr');
            
            let color = "var(--text-main)";
            if(data.SuperTrend === "YÜKSELİŞ") color = "var(--accent-green)";
            if(data.SuperTrend === "DÜŞÜŞ") color = "var(--accent-red)";
            
            let periodName = period;
            if (period === 'Weekly') periodName = "Haftalık";
            if (period === 'Monthly') periodName = "Aylık";
            if (period === 'Month_6') periodName = "6 Aylık";
            
            tr.innerHTML = `
                <td style="font-weight:bold;">${periodName}</td>
                <td style="color:${color}; font-weight:bold;">${data.SuperTrend || "-"}</td>
                <td>${data.MA8 || "-"}</td>
                <td>${data.MA21 || "-"}</td>
                <td>${data.MA50 || "-"}</td>
                <td>${data.MA200 || "-"}</td>
            `;
            mtfBody.appendChild(tr);
        }
    } else {
         mtfBody.innerHTML = "<tr><td colspan='6' class='text-muted' style='text-align:center;'>MTF Verisi Bulunamadı</td></tr>";
    }

    // Technical Indicators (Live)
    setElText('ti-rsi', safeGet(report, "Section_21_TechnicalIndicators.RSI_14", "-"));
    setElText('ti-ema20', safeGet(report, "Section_21_TechnicalIndicators.EMA_20", "-"));
    setElText('ti-ema50', safeGet(report, "Section_21_TechnicalIndicators.EMA_50", "-"));
    setElText('ti-ema200', safeGet(report, "Section_21_TechnicalIndicators.EMA_200", "-"));

    const fcBody = document.getElementById('fc-body');
    if (fcBody) {
        fcBody.innerHTML = "";
        const fc = safeGet(report, "Section_17_Forecast", {});
        const fcLabels = { "1d": "1 Gün", "1w": "1 Hafta", "1m": "1 Ay", "3m": "3 Ay", "6m": "6 Ay", "12m": "12 Ay" };
        ["1d", "1w", "1m", "3m", "6m", "12m"].forEach(p => {
            if(fc[p]) {
                let tr = document.createElement('tr');
                tr.innerHTML = `<td>${fcLabels[p] || p}</td><td class="text-blue">${fc[p]}</td>`;
                fcBody.appendChild(tr);
            }
        });
        if (!fcBody.children.length) {
            fcBody.innerHTML = '<tr><td colspan="2" style="text-align:center; color:var(--text-muted);">Tahmin verisi bulunamadı</td></tr>';
        }
    }

    setElText('sc-bull', safeGet(report, "Section_16_Scenario.Bull.Price"));
    setElText('sc-bull-p', safeGet(report, "Section_16_Scenario.Bull.Prob"));
    setElText('sc-base', safeGet(report, "Section_16_Scenario.Base.Price"));
    setElText('sc-base-p', safeGet(report, "Section_16_Scenario.Base.Prob"));
    setElText('sc-bear', safeGet(report, "Section_16_Scenario.Bear.Price"));
    setElText('sc-bear-p', safeGet(report, "Section_16_Scenario.Bear.Prob"));

    // 4. FUNDAMENTAL & MACRO TAB
    // Ratios
    let sector = t(safeGet(report, "Section_22_FundamentalRatios.Sector", "-"));
    let industry = t(safeGet(report, "Section_22_FundamentalRatios.Industry", "-"));
    setElText('fa-sector', (sector !== "-" && industry !== "-") ? `${sector} / ${industry}` : "Bulunamadı (API)");
    
    setElText('fa-pe', t(safeGet(report, "Section_22_FundamentalRatios.P_E_Ratio", "-")));
    setElText('fa-pb', t(safeGet(report, "Section_22_FundamentalRatios.P_B_Ratio", "-")));
    setElText('fa-roe', t(safeGet(report, "Section_22_FundamentalRatios.ROE", "-")));
    setElText('fa-debt', t(safeGet(report, "Section_22_FundamentalRatios.Debt_to_Equity", "-")));
    setElText('fa-margin', t(safeGet(report, "Section_22_FundamentalRatios.Profit_Margin", "-")));

    // Macro
    setElText('mac-vix', t(safeGet(report, "Section_23_Macro.VIX_Level", "-")));
    setElText('mac-regime', t(safeGet(report, "Section_23_Macro.Regime", "-")));
    setElText('mac-trend', t(safeGet(report, "Section_23_Macro.Market_Trend", "-")));

    setElText('pa-fit', safeGet(report, "Section_13_Portfolio.Fit"));
    setElText('pa-corr', safeGet(report, "Section_13_Portfolio.Correlation"));
    setElText('pa-warn', safeGet(report, "Section_13_Portfolio.Sector_Warning"));

    setElText('ew-risk', safeGet(report, "Section_15_EarlyWarning.Risk"));
    setElText('ew-opp', safeGet(report, "Section_15_EarlyWarning.Opportunity"));
    setElText('lm-alert', safeGet(report, "Section_20_LiveMonitor.Alert"));

    setElText('sr-ana', safeGet(report, "Section_18_Reliability.Analogues"));
    setElText('sr-hit', safeGet(report, "Section_18_Reliability.Hit_Rate"));
    setElText('sr-risk', safeGet(report, "Section_18_Reliability.Monte_Carlo_Risk"));

    // 5. REASONING TAB (COMMITTEE & 7 WHYS)
    const reasoning = safeGet(report, "Section_19_Reasoning", {});
    setElText('cio-verdict', reasoning.CIO_Verdict || "-");

    const comBody = document.getElementById('com-body');
    comBody.innerHTML = "";
    if (reasoning.Committee_Votes) {
        for (const [agent, info] of Object.entries(reasoning.Committee_Votes)) {
            let tr = document.createElement('tr');
            let voteVal = info.Vote || "BEKLE";
            let color = (voteVal.includes("AL") || voteVal === "ONAY") ? "var(--accent-green)" : 
                        ((voteVal.includes("SAT") || voteVal === "RED") ? "var(--accent-red)" : "var(--accent-yellow)");
            tr.innerHTML = `<td>${agent.replace("_AI","")}</td><td style="color:${color};font-weight:700;">${voteVal}</td><td>${info.Score || 50}</td><td style="font-size:0.85rem; color:var(--text-muted);">${info.Reasoning || "-"}</td>`;
            comBody.appendChild(tr);
        }
    }

    const whysCont = document.getElementById('whys-container');
    whysCont.innerHTML = "";
    if (reasoning.The_7_Whys) {
        for (const [q, a] of Object.entries(reasoning.The_7_Whys)) {
            let div = document.createElement('div');
            div.className = "why-item";
            div.innerHTML = `<div class="why-q">${q.replace(/_/g, ' ')}</div><div class="why-a">${a}</div>`;
            whysCont.appendChild(div);
        }
    }
    
    // 6. RAW JSON TAB
    setElText('raw-json-output', JSON.stringify(report, null, 2));

    // 7. ALTIN VARANT DETAYLI SİMÜLASYONUNU YÜKLE
    try {
        let spotPrice = safeGet(report, "Section_01_Ident.Price", 100);
        loadDetailedVarantSim(currentSymbol, spotPrice);
    } catch(e) {
        console.error("Detaylı varant simülasyonu başlatılamadı:", e);
    }
}

// ========== CHART.JS INTEGRATION ==========
function drawScoreChart(confidence, risk) {
    const ctx = document.getElementById('scoreChart').getContext('2d');
    
    if (chartInstance) {
        chartInstance.destroy();
    }

    // A clean polar area chart or doughnut chart to represent AI scores
    chartInstance = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Güven Skoru', 'Risk Profili', 'Kalan'],
            datasets: [{
                data: [confidence, risk, 100 - (confidence + risk)/2],
                backgroundColor: [
                    '#10B981', // green for confidence
                    '#EF4444', // red for risk
                    '#1E293B'  // card bg for remaining
                ],
                borderWidth: 0,
                hoverOffset: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '75%',
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: { color: '#94A3B8', font: { family: 'system-ui', size: 11 } }
                }
            }
        }
    });
}

// ========== RADAR SCAN ==========
async function startRadar(type) {
    let endpoint = '/api/scan';
    if (type === 'varant') endpoint = '/api/scan_warrants';
    else if (type === 'allbist') endpoint = '/api/scan_all';
    else if (type === 'fx') endpoint = '/api/scan_fx';
    else if (type === 'commodity') endpoint = '/api/scan_commodity';
    else if (type === 'crypto') endpoint = '/api/scan_crypto';
    else if (type === 'mtf') endpoint = '/api/scan_mtf';
    
    const loadingEl = document.getElementById(type + '-loading');
    const resultsEl = document.getElementById(type + '-results');
    const tbodyEl = document.getElementById(type + '-tbody');

    if (loadingEl) loadingEl.style.display = 'block';
    if (resultsEl && (!tbodyEl || !tbodyEl.children.length)) resultsEl.style.display = 'none';

    try {
        const response = await fetch(endpoint);
        const data = await response.json();

        if (loadingEl) loadingEl.style.display = 'none';
        if (resultsEl) resultsEl.style.display = 'table';
        if (tbodyEl) tbodyEl.innerHTML = '';

        if (!data.results || data.results.length === 0) {
            if (tbodyEl) tbodyEl.innerHTML = `<tr><td colspan='4' style='text-align:center; color: var(--text-muted); padding:2rem;'><i class="fa-solid fa-circle-exclamation text-yellow" style="font-size:1.5rem; display:block; margin-bottom:8px;"></i>Bu kategoride henüz güçlü sinyal oluşmadı. Sistem piyasayı izlemeye devam ediyor.</td></tr>`;
            return;
        }

        data.results.forEach(res => {
            let tr = document.createElement('tr');
            let scoreValue = res.Score !== undefined ? res.Score : (res.Confidence_Score !== undefined ? res.Confidence_Score : 0);
            let scoreColor = scoreValue >= 75 ? 'var(--accent-green)' : (scoreValue >= 60 ? 'var(--accent-blue)' : (scoreValue >= 45 ? 'var(--accent-yellow)' : 'var(--accent-red)'));
            
            let priceStr = res.Price ? `₺${parseFloat(res.Price).toFixed(2)}` : '';
            if (res.Change_Pct !== undefined) {
                let cp = parseFloat(res.Change_Pct);
                let cpColor = cp > 0 ? 'var(--accent-green)' : (cp < 0 ? 'var(--accent-red)' : 'var(--text-muted)');
                let cpSign = cp > 0 ? '+' : '';
                priceStr += ` <span style="font-size:0.75rem; color:${cpColor}; font-weight:700;">(${cpSign}%${cp.toFixed(2)})</span>`;
            }

            let trendVal = res.Trend || 'BULLISH';
            let trendIcon = (trendVal === 'BULLISH' || trendVal === 'YUKSEK') ? 'fa-arrow-trend-up' : ((trendVal === 'BEARISH' || trendVal === 'DUSUK') ? 'fa-arrow-trend-down' : 'fa-minus');
            let trendColor = (trendVal === 'BULLISH' || trendVal === 'YUKSEK') ? 'var(--accent-green)' : ((trendVal === 'BEARISH' || trendVal === 'DUSUK') ? 'var(--accent-red)' : 'var(--text-muted)');

            let actionText = res.Action || (scoreValue >= 65 ? "GÜÇLÜ AL" : (scoreValue >= 50 ? "AL" : "İZLE"));
            let actionBg = scoreValue >= 65 ? 'rgba(16,185,129,0.15)' : (scoreValue >= 50 ? 'rgba(56,189,248,0.15)' : 'rgba(234,179,8,0.15)');
            let actionColor = scoreValue >= 65 ? 'var(--accent-green)' : (scoreValue >= 50 ? 'var(--accent-blue)' : 'var(--accent-yellow)');

            tr.innerHTML = `
                <td style="color:var(--text-main); font-weight:700;">
                    <div style="font-size:0.92rem; color:var(--text-light);">${res.Symbol}</div>
                    ${priceStr ? `<div style="font-size:0.75rem; font-family:monospace; margin-top:2px;">${priceStr}</div>` : ''}
                </td>
                <td><span style="color:${scoreColor}; font-weight:800; font-size:0.9rem; background:rgba(255,255,255,0.04); border:1px solid ${scoreColor}40; padding:2px 8px; border-radius:6px;">${scoreValue} / 100</span></td>
                <td><span style="color:${trendColor}; font-weight:700; font-size:0.85rem;"><i class="fa-solid ${trendIcon}" style="margin-right:4px;"></i> ${t(trendVal)}</span></td>
                <td>
                    <span style="background:${actionBg}; color:${actionColor}; padding:3px 8px; border-radius:4px; font-weight:700; font-size:0.75rem;">${t(actionText)}</span>
                </td>
            `;
            tbodyEl.appendChild(tr);
        });

    } catch (error) {
        if (loadingEl) loadingEl.style.display = 'none';
        if (tbodyEl) tbodyEl.innerHTML = `<tr><td colspan='4' class="text-red text-center" style="padding:1.5rem;">Tarama sırasında bağlantı hatası: ${error.message || error}</td></tr>`;
        if (resultsEl) resultsEl.style.display = 'table';
    }
}

// ========== FAZ 6: BULK DASHBOARD & INITIALIZATION ==========
let globalDashboardData = {};

// ===== DESTEK / DIRENC HUCRESI (dip radar verisinden) =====
function _srLookup(symbol) {
    if (!symbol) return null;
    const bare = String(symbol).replace('.IS', '');
    return (dipRowsCache || []).find(r => r.symbol === bare) || null;
}

function srCellHtml(symbol, price) {
    const r = _srLookup(symbol);
    if (!r || !r.support) return '<span style="color:var(--text-muted); font-size:0.75rem;">—</span>';
    const p = parseFloat(price) || r.price;
    const supPct = ((p - r.support) / r.support * 100).toFixed(1);
    const resPct = ((r.resistance - p) / p * 100).toFixed(1);
    const supColor = Math.abs(supPct) <= 3 ? 'var(--accent-green)' : 'var(--text-muted)';
    const resColor = Math.abs(resPct) <= 3 ? 'var(--accent-green)' : (Math.abs(resPct) <= 8 ? '#f59e0b' : 'var(--text-muted)');
    return `<div style="font-size:0.72rem; line-height:1.5; white-space:nowrap;">
        <span style="color:var(--text-muted);">Ş</span> <b>₺${p.toFixed(2)}</b><br>
        <span title="Destek (altında tepki alınmış bölge)" style="color:${supColor};">🟢 D: ₺${r.support.toFixed(2)} (-${supPct}%)</span><br>
        <span title="Direnç (üstünde tepe bölgesi)" style="color:${resColor};">🔴 Y: ₺${r.resistance.toFixed(2)} (+${resPct}%)</span>
    </div>`;
}

let dashboardPollInterval = null;

window.onload = function() {
    const urlParams = new URLSearchParams(window.location.search);
    const sym = urlParams.get('symbol');
    const tab = urlParams.get('tab');
    if (sym && tab === 'graphic') {
        document.getElementById('symbol-input').value = sym;
        analyzeSymbol();
    }
    
    fetchDashboardData();
    // Her 5 saniyede bir arka plandaki scanner'in bitip bitmediğini kontrol et
    dashboardPollInterval = setInterval(fetchDashboardData, 5000);
    
    // KULLANICI İSTEĞİ: TABLOYA ÇİFT TIKLAYINCA TAM TABLOYU TEK GÖSTER
    document.querySelectorAll('#radar-cards-grid .card').forEach(card => {
        card.ondblclick = function(e) {
            // Eğer butona veya input'a çift tıklandıysa büyütme
            if (e.target.closest('button') || e.target.closest('input') || e.target.closest('a')) {
                return;
            }
            this.classList.toggle('fullscreen-card');
        };
        // Kullanıcının anlaması için imleci pointer veya title ekleyebiliriz
        card.title = "Tam ekran yapmak için çift tıklayın";
    });
};

async function fetchDashboardData() {
    try {
        const response = await fetch('/api/dashboard_init?t=' + Date.now());
        if (!response.ok) {
            console.error("Dashboard HTTP error: ", response.status);
            return;
        }
        const data = await response.json();
        
        if (data && data.status === 'success') {
            setElText('total-analyzed-counter', `RADAR BUGÜNE KADAR ${data.total_analyzed || 0} VERİYİ ANALİZ ETTİ`);
            const shieldEl = document.getElementById('shield-status');
            if (shieldEl) {
                const chg = data.xu100_change || 0;
                if (chg <= -1.0) {
                    shieldEl.innerHTML = `<span style="color:#ef4444; font-size:1.1rem;"><i class="fa-solid fa-triangle-exclamation"></i> Ayı (%100 Nakit)</span>`;
                } else if (chg <= 0.0) {
                    shieldEl.innerHTML = `<span style="color:var(--accent-yellow); font-size:1.1rem;"><i class="fa-solid fa-scale-balanced"></i> Dalgalı (%60 Nakit)</span>`;
                } else {
                    shieldEl.innerHTML = `<span style="color:var(--accent-green); font-size:1.1rem;"><i class="fa-solid fa-arrow-trend-up"></i> Boğa (%30 Nakit)</span>`;
                }
            }

            
            // Son tarama saatini ekranda göster
            const lastUpdated = data.last_updated || "Bilinmiyor";
            const timeHTML = `<i class="fa-solid fa-clock"></i> Son Tarama: ${lastUpdated}`;
            const timeEl1 = document.getElementById('last-scan-time');
            if (timeEl1) timeEl1.innerHTML = timeHTML;
            const timeEl2 = document.getElementById('arge-last-scan');
            if (timeEl2) timeEl2.innerHTML = timeHTML;
            
            console.log('[DASHBOARD] API cevabı geldi. Keys:', Object.keys(data.dashboard_data || {}), 
                'opp1h:', (data.dashboard_data?.opportunities_1h || []).length,
                'opp:', (data.dashboard_data?.opportunities || []).length);
            
            // Eğer veri doluysa tabloları doldur
            if (data.dashboard_data && Object.keys(data.dashboard_data).length > 0) {
                globalDashboardData = data.dashboard_data;
                
                // Render all categories
                renderAllDashboardTables();
                
                if (dashboardPollInterval) {
                    clearInterval(dashboardPollInterval);
                    dashboardPollInterval = null;
                    // Arka plandaki periyodik güncellemeleri yakalamak için 30 saniyede bir kontrol et
                    setInterval(fetchDashboardData, 30000);
                }
            } else {
                console.log('[DASHBOARD] Veri henüz boş veya tarama devam ediyor...');
                // Hâlâ boşsa kullanıcıyı bilgilendir
                ["tb-signals-5m", "tb-tavan-adaylari", "tb-opportunities-1h", "tb-stay-away-1h", "tb-opportunities", "tb-gainers", "tb-losers", "tb-favorites", "tb-high_volume", "tb-low_volume"].forEach(id => {
                    const tbody = document.getElementById(id);
                    if (tbody && (tbody.innerText.includes("Taran") || tbody.innerHTML.includes("Taran"))) {
                        tbody.innerHTML = `<tr><td colspan="5" style="text-align: center;" class="text-muted">Piyasa kapalı veya tarama devam ediyor (00:00-09:00 arası veri bulunmayabilir).</td></tr>`;
                    }
                });
            }
        }
    } catch (e) {
        console.error("Dashboard Init Error: ", e);
    }
}

// Clock updates
setInterval(updateLiveClock, 1000);

function updateLiveClock() {
    const clockEl = document.getElementById('live-clock');
    const dateEl = document.getElementById('live-date');
    if (clockEl && dateEl) {
        const now = new Date();
        clockEl.innerText = now.toLocaleTimeString('tr-TR');
        dateEl.innerText = now.toLocaleDateString('tr-TR', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' }).toLocaleUpperCase('tr-TR');
    }
}

function openGraphicTab(symbol) {
    document.getElementById('symbol-input').value = symbol;
    analyzeSymbol();
}

function renderAllDashboardTables() {
    const cats = {
        'tavan_adaylari': 'tb-tavan-adaylari',
        'arge_tavan': 'tb-arge-tavan',
        'opportunities_1h': 'tb-opportunities-1h',
        'stay_away_1h': 'tb-stay-away-1h',
        'opportunities': 'tb-opportunities',
        'defensive_stocks': 'defensive-tbody',
        'gainers': 'tb-gainers',
        'losers': 'tb-losers',
        'favorites': 'tb-favorites',
        'high_volume': 'tb-high_volume',
        'low_volume': 'tb-low_volume'
    };

    // Canlı Giriş Ekranı: Otonom Komite Liderleri ve Tavsiyelerini Güncelle
    const homePicksContainer = document.getElementById('home-top-picks');
    if (homePicksContainer) {
        let bestItems = [];
        if (globalDashboardData['tavan_adaylari'] && globalDashboardData['tavan_adaylari'].length > 0) {
            bestItems.push(...globalDashboardData['tavan_adaylari'].slice(0, 2));
        }
        if (globalDashboardData['opportunities_1h'] && globalDashboardData['opportunities_1h'].length > 0) {
            bestItems.push(...globalDashboardData['opportunities_1h'].slice(0, 2));
        }
        if (globalDashboardData['opportunities'] && globalDashboardData['opportunities'].length > 0) {
            bestItems.push(...globalDashboardData['opportunities'].slice(0, 2));
        }
        
        // Benzersiz sembolleri al ve ilk 3 tanesini yerleştir
        const uniqueSymbols = [];
        const seenSyms = new Set();
        for (let item of bestItems) {
            if (item && item.Symbol && !seenSyms.has(item.Symbol)) {
                seenSyms.add(item.Symbol);
                uniqueSymbols.push(item);
            }
        }
        
        if (uniqueSymbols.length > 0) {
            const top3 = uniqueSymbols.slice(0, 3);
            const colors = ["var(--accent-green)", "var(--accent-blue)", "var(--accent-purple)"];
            homePicksContainer.innerHTML = "";
            top3.forEach((item, idx) => {
                let sVal = item.Score !== undefined ? item.Score : (item.Score_5 ? item.Score_5 * 20 : 85);
                let col = colors[idx] || "var(--accent-green)";
                let priceStr = item.Price ? `₺${parseFloat(item.Price).toFixed(2)}` : '';
                homePicksContainer.innerHTML += `
                    <button type="button" onclick="document.getElementById('symbol-input').value='${item.Symbol}'; analyzeSymbol();" style="flex:1; background:rgba(255,255,255,0.04); border:1px solid rgba(255,255,255,0.1); border-radius:6px; padding:0.5rem; color:var(--text-light); cursor:pointer; font-size:0.78rem; text-align:center; transition:transform 0.2s;" onmouseover="this.style.transform='translateY(-2px)'" onmouseout="this.style.transform='none'">
                        <div style="font-weight:800; color:${col};">${item.Symbol} <span style="font-size:0.7rem; color:var(--text-light); font-weight:normal;">${priceStr}</span></div>
                        <div style="font-size:0.7rem; color:var(--text-muted); margin-top:2px;">Komite Skoru: <b style="color:${col};">${sVal}</b></div>
                    </button>
                `;
            });
        }
    }

    for (let cat in cats) {
        const tbody = document.getElementById(cats[cat]);
        if (!tbody) continue;
        
        let items = globalDashboardData[cat] || [];
        
        if (cat === 'arge_tavan') {
            items = globalDashboardData['tavan_adaylari'] || [];
        }

        if (items.length === 0) {
            tbody.innerHTML = `<tr><td colspan="7" style="text-align: center;" class="text-muted">Bu kategoride sonuç bulunamadı.</td></tr>`;
            continue;
        }

        // EMA 50 & 200 filtresini her zaman uygula (Defansif hisseler kendi kuralına sahiptir, hariç tut)
        if (cat !== 'defensive_stocks' && cat !== 'losers') {
            items = items.filter(res => {
                let price = res.Price || res.Daily_Close;
                let ema50 = res.Daily_EMA50;
                let ema200 = res.Daily_EMA200;
                
                if (ema50 === undefined && res.Indicators) ema50 = res.Indicators.EMA_50;
                if (ema200 === undefined && res.Indicators) ema200 = res.Indicators.EMA_200;
                
                if (price && ema50 && ema200) {
                    return price > ema50 && price > ema200;
                }
                return true;
            });
        }
        
        if (items.length === 0) {
            tbody.innerHTML = `<tr><td colspan="7" style="text-align: center;" class="text-muted">Filtreye uygun hisse bulunamadı (EMA 50 & 200 Üzeri).</td></tr>`;
            continue;
        }

        // "Squaze (yukarı ok) + Güçlü Giriş + Pozitif Alpha" kontrolü için yardımcı fonksiyon
        const checkSuperGreen = (res) => {
            let alphaStrVal = res.Alpha_Str || "";
            let sqzStrVal = res.Short_Squeeze || "";
            let smStrVal = res.Smart_Money || "";
            return (alphaStrVal.includes("Pozitif") && 
                (smStrVal.includes("Giriş") || smStrVal.includes("Akümülasyon")) &&
                (sqzStrVal.includes("Yükseliyor") || sqzStrVal.includes("Patlatma")));
        };

        // Eğer bu Tavan Adayları veya AR-GE tablosu ise, Super Green olanları en başa al
        if (cat === 'tavan_adaylari' || cat === 'arge_tavan') {
            let superGreenItems = [];
            let regularItems = [];
            items.forEach(item => {
                if (checkSuperGreen(item)) {
                    superGreenItems.push(item);
                } else {
                    regularItems.push(item);
                }
            });
            items = superGreenItems.concat(regularItems);
        }

        tbody.innerHTML = '';
        // 10'a kadar hisse göster
        const displayItems = items.slice(0, 10);
        let timeStr = new Date().toLocaleTimeString('tr-TR', {hour: '2-digit', minute: '2-digit'});
        const headerTimeSpan = document.getElementById('time-' + (cat === 'opportunities_1h' ? 'opportunities-1h' : (cat === 'stay_away_1h' ? 'stay-away-1h' : cat)));
        if (headerTimeSpan) {
            headerTimeSpan.innerText = "(Güncelleme: " + timeStr + ")";
        }

        displayItems.forEach(res => {
            let tr = document.createElement('tr');
            
            let isSuperGreen = checkSuperGreen(res);
            tr.className = isSuperGreen ? "super-green-row card-fade-in" : "card-fade-in";
            
            let symStr = res.Symbol;
            if (isSuperGreen) {
                symStr += ` <i class="fa-solid fa-rocket" style="color:var(--accent-green); text-shadow: 0 0 8px var(--accent-green);" title="Süper Kesişim: Squeeze⬆️ + Para Girişi + Pozitif Alpha"></i>`;
            }
            
            // Eger bu hisse icin 5m RSI sinyali varsa blink ikonu ekle
            if (globalDashboardData['signals_5m'] && (cat === 'tavan_adaylari' || cat === 'opportunities_1h')) {
                let sigObj = globalDashboardData['signals_5m'].find(s => s.Symbol === res.Symbol);
                if (sigObj) {
                    if (sigObj.Signal === "AL") {
                        symStr += ` <i class="fa-solid fa-circle blink-green" title="5m AL Sinyali"></i>`;
                    } else if (sigObj.Signal === "SAT") {
                        symStr += ` <i class="fa-solid fa-circle blink-red" title="5m SAT Sinyali"></i>`;
                    }
                }
            }

                    // MTF Radar ile Kesisim Kontrolu (Altin Firsat)
                    let mtfMatch = false;
                    if (globalDashboardData['mtf_results'] && Array.isArray(globalDashboardData['mtf_results'])) {
                        mtfMatch = globalDashboardData['mtf_results'].some(m => m.Symbol === res.Symbol);
                    }
                    if (mtfMatch && (cat === 'tavan_adaylari' || cat === 'opportunities_1h')) {
                        symStr += ` <span style="background: linear-gradient(90deg, #fbbf24, #d97706); color: black; padding: 2px 6px; border-radius: 4px; font-size: 0.65rem; font-weight: bold; margin-left: 5px; box-shadow: 0 0 10px rgba(251,191,36,0.6); animation: pulse 2s infinite;" title="Altın Fırsat: Hem Tavan/1S Radarı hem de MTF İvme (1S/15D) Radarı eşleşti!"><i class="fa-solid fa-crown"></i> ALTIN</span>`;
                        tr.style.borderLeft = "3px solid #fbbf24";
                        tr.style.backgroundColor = "rgba(251,191,36,0.05)";
                    }
            
            let priceStr = res.Price ? "₺" + parseFloat(res.Price).toFixed(2) : "-";
            
            if (res.Change_Pct !== undefined && cat !== 'gainers' && cat !== 'losers' && cat !== 'opportunities_1h') {
                let p_pct = parseFloat(res.Change_Pct);
                let p_c = p_pct > 0 ? "var(--accent-green)" : (p_pct < 0 ? "var(--accent-red)" : "var(--text-muted)");
                let p_sign = p_pct > 0 ? "+" : "";
                priceStr += `<br><span style="color:${p_c}; font-size:0.75rem;">(${p_sign}%${p_pct.toFixed(2)})</span>`;
            }

            let statusStr = "";
            let scoreContent = "";
            if (cat === 'arge_tavan') {
                // 1. Aday Hisse & Fiyat
                
                // 2. Alpha (BIST Ayrışma)
                let alphaStr = res.Alpha_Str || "Hesaplanıyor";
                let alphaColor = alphaStr.includes("Pozitif") ? "var(--accent-green)" : (alphaStr.includes("Negatif") ? "var(--accent-red)" : "var(--accent-yellow)");
                let alphaIcon = alphaStr.includes("Pozitif") ? "fa-arrow-trend-up" : (alphaStr.includes("Negatif") ? "fa-arrow-trend-down" : "fa-minus");
                let alphaEl = `<span style="color:${alphaColor}; font-weight:800; font-size:0.8rem;"><i class="fa-solid ${alphaIcon}"></i> ${alphaStr}</span>`;
                
                // 3. Squeeze (Şort)
                let sqzStr = res.Short_Squeeze || "Hesaplanıyor";
                let sqzColor = sqzStr.includes("Patlatma") ? "var(--accent-red)" : (sqzStr.includes("Yükseliyor") ? "var(--accent-yellow)" : "var(--text-muted)");
                let sqzIcon = sqzStr.includes("Patlatma") ? "fa-fire fa-beat" : (sqzStr.includes("Yükseliyor") ? "fa-arrow-up" : "fa-minus");
                let sqzEl = `<span style="color:${sqzColor}; font-weight:800; font-size:0.8rem;"><i class="fa-solid ${sqzIcon}"></i> ${sqzStr}</span>`;

                // 4. Akıllı Para (CMF)
                let smStr = res.Smart_Money || "Hesaplanıyor";
                let smColor = smStr.includes("Giriş") || smStr.includes("Akümülasyon") ? "var(--accent-green)" : (smStr.includes("Çıkış") || smStr.includes("Dağıtım") ? "var(--accent-red)" : "var(--accent-yellow)");
                let smEl = `<span style="color:${smColor}; font-weight:800; font-size:0.8rem;">${smStr}</span>`;
                
                // 5. Domino Etkisi
                let domStr = res.Domino_Str || "Yok";
                let domColor = domStr !== "Yok" ? "var(--accent-blue)" : "var(--text-muted)";
                let domIcon = domStr !== "Yok" ? "fa-chess-knight" : "fa-ban";
                let domEl = `<span style="color:${domColor}; font-weight:700; font-size:0.75rem;"><i class="fa-solid ${domIcon}"></i> ${domStr}</span>`;

                // 6. Patlama Olasılığı (P-Score)
                let pScore = res.Score !== undefined ? res.Score : 0;
                let pScoreColor = pScore >= 80 ? 'var(--accent-green)' : (pScore >= 50 ? 'var(--accent-yellow)' : 'var(--accent-red)');
                let pScoreStr = `
                    <div style="width:100%; max-width:80px; background:rgba(255,255,255,0.1); border-radius:4px; overflow:hidden; margin-bottom:4px;">
                        <div style="height:6px; background:${pScoreColor}; width:${pScore}%"></div>
                    </div>
                    <span style="color:${pScoreColor}; font-weight:800; font-size:0.85rem;">%${pScore}</span>
                `;
                
                tr.innerHTML = `
                    <td style="color:var(--accent-purple);font-weight:700; font-size:1rem;">${symStr} <span style="font-size:0.7rem; color:var(--text-muted);">${priceStr}</span></td>
                    <td>${alphaEl}</td>
                    <td>${sqzEl}</td>
                    <td>${smEl}</td>
                    <td>${domEl}</td>
                    <td>${pScoreStr}</td>
                    <td>${srCellHtml(res.Symbol, res.Price)}</td>
                `;
                tbody.appendChild(tr);
                return; // Skip the rest of the loop for this row
            } else if (cat === 'tavan_adaylari') {
                let scoreValue = res.Score !== undefined ? res.Score : 0;
                let scoreColor = scoreValue >= 85 ? 'var(--accent-green)' : (scoreValue >= 75 ? 'var(--accent-yellow)' : 'var(--text-muted)');
                
                // Evre Rozeti (Phase Badge) & V-Dönüş
                let phaseBadge = res.Phase_Badge || 'TAVAN';
                let phaseColor = res.Phase_Color || 'green';
                let phaseBg = phaseColor === 'red' ? 'rgba(239, 68, 68, 0.2)' : (phaseColor === 'yellow' ? 'rgba(234, 179, 8, 0.2)' : 'rgba(16, 185, 129, 0.2)');
                let phaseTxtColor = phaseColor === 'red' ? 'var(--accent-red)' : (phaseColor === 'yellow' ? 'var(--accent-yellow)' : 'var(--accent-green)');
                let phaseIcon = phaseColor === 'red' ? 'fa-lock' : (phaseColor === 'yellow' ? 'fa-bolt' : 'fa-seedling');
                let phaseTooltip = phaseBadge.includes("KİLİTLEME") ? "Tavana kilitlenme aşaması. Alım riski yüksek." : (phaseBadge.includes("İVMELENME") ? "Hacimle birlikte sert yukarı momentum başladı." : "Trendin başlangıcı. Yüksek kazanç potansiyeli.");
                let evreStr = `<span title="${phaseTooltip}" style="background:${phaseBg}; color:${phaseTxtColor}; padding:3px 7px; border-radius:4px; font-weight:700; font-size:0.72rem; white-space:nowrap; cursor:help;"><i class="fa-solid ${phaseIcon}"></i> ${phaseBadge}</span>`;
                
                // 🛡️ Anti-Trap Shield (Tuzak Önleme Rozeti) & Teyit Skoru
                if (res.Anti_Trap_Badge) {
                    let atColor = res.Anti_Trap_Color || '#10b981';
                    let atBg = atColor === '#10b981' ? 'rgba(16, 185, 129, 0.15)' : (atColor === '#ef4444' ? 'rgba(239, 68, 68, 0.2)' : 'rgba(234, 179, 8, 0.15)');
                    evreStr += `<div style="margin-top:3px;"><span title="Tuzak Kalkanı: Kurumsal para girişi ve mum formasyonu ile alım onayı." style="background:${atBg}; color:${atColor}; border:1px solid ${atColor}; padding:2px 5px; border-radius:3px; font-size:0.68rem; font-weight:700; white-space:nowrap; cursor:help;">${res.Anti_Trap_Badge}</span></div>`;
                }

                if (res.ORB_Breakout) {
                    evreStr += `<div style="margin-top:2px;"><span title="Açılış Aralığı Kırılımı (ORB): Hisse günün ilk saatlerindeki tepe noktasını hacimli şekilde yukarı kırdı." style="background:rgba(56, 189, 248, 0.15); color:#38bdf8; border:1px solid #38bdf8; padding:1px 4px; border-radius:3px; font-size:0.66rem; font-weight:700; cursor:help;"><i class="fa-solid fa-bullseye"></i> ORB Açılış Kırılımı</span></div>`;
                }

                if (res.V_Reversal) {
                    evreStr += `<div style="margin-top:3px;"><span title="V-Dönüş: Gün içi dip seviyesinden çok hızlı ve güçlü bir şekilde toparlanıp ivme kazandı." style="background:rgba(168, 85, 247, 0.2); color:#c084fc; padding:2px 5px; border-radius:3px; font-size:0.68rem; font-weight:700; cursor:help;"><i class="fa-solid fa-bolt-lightning"></i> V-Dönüş +%${(res.V_Power||0).toFixed(1)}</span></div>`;
                }
                
                // Tavan Fiyatı, Kalan % ve ETA
                let tavanPVal = res.Ceiling_Price || (res.Position && res.Position.TP2 ? res.Position.TP2 : null);
                let curPVal = res.Price || (res.Position && res.Position.Entry ? res.Position.Entry : null);
                let distPct = "-";
                if (res.Distance_To_Ceiling_Pct !== undefined && !isNaN(parseFloat(res.Distance_To_Ceiling_Pct))) {
                    distPct = parseFloat(res.Distance_To_Ceiling_Pct).toFixed(1);
                } else if (tavanPVal && curPVal && curPVal > 0) {
                    distPct = (((tavanPVal - curPVal) / curPVal) * 100).toFixed(1);
                }
                let tavanP = tavanPVal ? "₺" + parseFloat(tavanPVal).toFixed(2) : "-";
                let etaVal = res.ETA || (res.Position ? res.Position.Projection : "-");
                let tavanStr = `<div style="font-size:0.88rem; font-weight:700; color:var(--accent-green); font-family:monospace;">${tavanP}</div>
                                <div style="font-size:0.75rem; color:var(--text-muted);">Kalan: <b style="color:var(--accent-blue);">+${distPct}%</b></div>
                                <div style="font-size:0.7rem; color:var(--text-muted); margin-top:2px;" title="Tahmini Tavan Saati"><i class="fa-regular fa-clock"></i> ${etaVal}</div>`;
                
                // Hacim Katlama & Mum Gücü & VWAP & Domino
                let volM = res.Vol_Multiplier !== undefined && !isNaN(parseFloat(res.Vol_Multiplier)) ? parseFloat(res.Vol_Multiplier).toFixed(1) : "1.0";
                let volColor = volM >= 2.5 ? 'var(--accent-green)' : (volM >= 1.5 ? 'var(--accent-yellow)' : 'var(--text-muted)');
                let hacimStr = `<span style="color:${volColor}; font-weight:700; font-size:0.75rem;"><i class="fa-solid fa-fire"></i> ${volM}x Hacim</span>`;
                
                if (res.VWAP) {
                    hacimStr += `<div style="font-size:0.68rem; color:var(--text-muted); margin-top:2px;" title="Hacim Ağırlıklı Ortalama Fiyat">⚖️ VWAP: ₺${parseFloat(res.VWAP).toFixed(2)}</div>`;
                }

                if (res.Breakdown_Risk) {
                    hacimStr += `<br><span style="background:rgba(239, 68, 68, 0.25); color:var(--accent-red); padding:1px 5px; border-radius:3px; font-size:0.68rem; font-weight:800;"><i class="fa-solid fa-triangle-exclamation"></i> ÇÖZÜLME RİSKİ</span>`;
                } else if (res.Trap_Risk) {
                    hacimStr += `<br><span style="background:rgba(239, 68, 68, 0.2); color:var(--accent-red); padding:1px 5px; border-radius:3px; font-size:0.68rem; font-weight:700;"><i class="fa-solid fa-triangle-exclamation"></i> Tuzak Riski</span>`;
                } else if (res.Candle_Strength && res.Candle_Strength.includes('Marubozu')) {
                    hacimStr += `<br><span style="background:rgba(16, 185, 129, 0.2); color:var(--accent-green); padding:1px 5px; border-radius:3px; font-size:0.68rem; font-weight:700;"><i class="fa-solid fa-dumbbell"></i> Boğa Gücü</span>`;
                }
                
                if (res.Domino_Sector && res.Domino_Peers && res.Domino_Peers.length > 0) {
                    let pStr = res.Domino_Peers.slice(0, 2).map(p => '#' + p).join(' ');
                    hacimStr += `<div style="font-size:0.68rem; color:#94a3b8; margin-top:2px;" title="Sektörel Domino Kardeş Hisseleri"><i class="fa-solid fa-chess-knight"></i> ${res.Domino_Sector}: ${pStr}</div>`;
                }
                
                // SADE GORUNUM: hukum + tek satir rozetler + hedef/stop
                let sigQ = res.Signal_Quality || `${scoreValue}/100`;
                let sigColor = scoreColor;
                if (res.Signal_Quality) {
                    if (res.Signal_Quality.includes("ÇOK GÜÇLÜ AL")) sigColor = "var(--accent-green)";
                    else if (res.Signal_Quality.includes("GÜÇLÜ AL")) sigColor = "var(--accent-green)";
                    else if (res.Signal_Quality.includes("İZLE")) sigColor = "var(--accent-yellow)";
                    else if (res.Signal_Quality.includes("ZAYIF")) sigColor = "var(--accent-orange)";
                    else if (res.Signal_Quality.includes("UZAK DUR")) sigColor = "var(--accent-red)";
                }

                let scoreStr = `<div style="font-weight:800; color:${sigColor}; font-size:1.05rem;">${sigQ}</div>`;

                // risk seviyesi (RSI bazli)
                let risk_level = "Orta";
                let risk_color = "#f59e0b";
                let smart_money = "Nötr";
                let sm_color = "var(--text-muted)";
                if (res.Indicators && res.Indicators.RSI) {
                    let rsi = res.Indicators.RSI;
                    if (rsi > 65) { risk_level = "Yüksek"; risk_color = "var(--accent-red)"; }
                    else if (rsi < 40) { risk_level = "Düşük"; risk_color = "var(--accent-green)"; }
                    if (res.Indicators.MACD_Positive && rsi < 65) {
                        smart_money = "▲ Giriş"; sm_color = "var(--accent-green)";
                    } else if (!res.Indicators.MACD_Positive) {
                        smart_money = "▼ Çıkış"; sm_color = "var(--accent-red)";
                    }
                }
                if (res.Teyit_Score >= 80) {
                    smart_money = "▲ Giriş"; sm_color = "var(--accent-green)";
                }

                let chips = [];
                if (res.Teyit_Score) {
                    let tc = res.Teyit_Score >= 80 ? '#10b981' : (res.Teyit_Score >= 60 ? '#facc15' : '#ef4444');
                    chips.push(`<span title="Kurumsal para + mum teyit skoru" style="border:1px solid ${tc}; color:${tc}; padding:1px 6px; border-radius:4px; font-size:0.7rem; font-weight:700;">Teyit %${res.Teyit_Score}</span>`);
                }
                chips.push(`<span title="Risk seviyesi (RSI bazli)" style="color:${risk_color}; font-size:0.72rem; font-weight:700;">Risk: ${risk_level}</span>`);
                chips.push(`<span title="Kurumsal para yönü" style="color:${sm_color}; font-size:0.72rem; font-weight:700;">🐋 ${smart_money}</span>`);
                if (res.FOMO_Level) {
                    chips.push(`<span title="FOMO ${res.FOMO_Score ? res.FOMO_Score.toFixed(1) : ''}" style="color:${res.FOMO_Color || 'var(--text-muted)'}; font-size:0.72rem; font-weight:700;">🔥 ${res.FOMO_Level}</span>`);
                }
                scoreStr += `<div style="display:flex; gap:6px; flex-wrap:wrap; align-items:center; margin-top:5px;">${chips.join('')}</div>`;

                let p_val_sade = parseFloat(res.Price || 0);
                if (p_val_sade > 0) {
                    scoreStr += `<div style="font-size:0.78rem; margin-top:6px; font-family:monospace; white-space:nowrap;" title="Otomatik hedef ve stop (+%5 / -%3)">
                        <span style="color:#22c55e;">●</span> Hedef <b>₺${(p_val_sade * 1.05).toFixed(2)}</b>
                        <span style="color:var(--text-muted);"> | </span>
                        <span style="color:#ef4444;">●</span> Stop <b>₺${(p_val_sade * 0.97).toFixed(2)}</b>
                    </div>`;
                }

                if (res.Streak_Score) {
                    scoreStr += `<div style="font-size:0.68rem; color:#38bdf8;" title="Çift Tavan İhtimali"><i class="fa-solid fa-link"></i> %${res.Streak_Score} Seri</div>`;
                }
                
                if (res.Warrant_Match) {
                    scoreStr += `<div style="margin-top:2px;"><span style="background:rgba(234, 179, 8, 0.2); color:#facc15; padding:1px 4px; border-radius:3px; font-size:0.68rem; font-weight:700;" title="${res.Warrant_Match.Desc}"><i class="fa-solid fa-crosshairs"></i> Varant: ${res.Warrant_Match.Leverage} (+%${res.Warrant_Match.Potential_Gain_Pct})</span></div>`;
                }
                
                tr.innerHTML = `
                    <td style="color:var(--text-main);font-weight:700;">${symStr}</td>
                    <td style="font-family:monospace; font-weight:600;">${priceStr}</td>
                    <td>${evreStr}</td>
                    <td>${tavanStr}</td>
                    <td>${hacimStr}</td>
                    <td>${scoreStr}</td>
                    <td>${srCellHtml(res.Symbol, res.Price)}</td>
                `;
                tbody.appendChild(tr);
                return;
            } else if (cat === 'opportunities_1h') {
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
            } else {
                let scoreValue = res.Score !== undefined ? res.Score : 0;
                let scoreColor = scoreValue >= 70 ? 'var(--accent-green)' : (scoreValue >= 50 ? 'var(--accent-yellow)' : 'var(--accent-red)');
                scoreContent = `<span style="color:${scoreColor};font-weight:700;">${scoreValue}</span>`;

                if (cat === 'gainers' || cat === 'losers') {
                    let pct = res.Change_Pct ? parseFloat(res.Change_Pct) : 0;
                    let c = pct > 0 ? "var(--accent-green)" : "var(--accent-red)";
                    let sign = pct > 0 ? "+" : (pct < 0 ? "-" : "");
                    statusStr = `<span style="color:${c}; font-weight:bold;">${sign}%${Math.abs(pct).toFixed(2)}</span>`;
                } else if (cat === 'high_volume' || cat === 'low_volume') {
                    let mv = res.Money_Volume ? parseFloat(res.Money_Volume) : 0;
                    let mStr = mv > 1000000 ? (mv / 1000000).toFixed(1) + "M ₺" : mv.toFixed(0) + " ₺";
                    statusStr = `<span style="color:var(--text-muted);">${mStr}</span>`;
                } else {
                    statusStr = `<span style="color:var(--accent-green)">AL</span>`;
                }
            }
            
            tr.innerHTML = `
                <td style="color:var(--text-main);font-weight:700;">${symStr}</td>
                <td style="font-family:monospace; font-weight:600;">${priceStr}</td>
                <td>${scoreContent}</td>
                <td>${statusStr}</td>
                <td>${srCellHtml(res.Symbol, res.Price)}</td>
            `;
                tbody.appendChild(tr);
        });
    }
    
    // Ayrıca Radar Sayfasındaki 1 Saatlik Fırsatlar tablosunu da güncelle
    const opp1hTbody = document.getElementById('opp1h-tbody');
    if (opp1hTbody) {
        const opp1hItems = globalDashboardData['opportunities_1h'] || [];
        if (opp1hItems.length === 0) {
            opp1hTbody.innerHTML = `<tr><td colspan="5" style="text-align: center;" class="text-muted">Bu kategoride sonuç bulunamadı.</td></tr>`;
        } else {
            opp1hTbody.innerHTML = '';
            opp1hItems.forEach(res => {
                let tr = document.createElement('tr');
                let s5 = res.Score_5 !== undefined ? res.Score_5 : 0;
                let sColor = s5 === 5 ? 'var(--accent-green)' : (s5 >= 4 ? 'var(--accent-blue)' : 'var(--accent-yellow)');
                let priceStr = res.Price ? "₺" + parseFloat(res.Price).toFixed(2) : "-";
                
                if (res.Daily_Change_Pct !== undefined) {
                    let d_pct = parseFloat(res.Daily_Change_Pct);
                    let d_c = d_pct > 0 ? "var(--accent-green)" : (d_pct < 0 ? "var(--accent-red)" : "var(--text-muted)");
                    let d_sign = d_pct > 0 ? "+" : "";
                    priceStr += `<br><span style="color:${d_c}; font-size:0.75rem;">(${d_sign}%${Math.abs(d_pct).toFixed(2)})</span>`;
                }
                
                let details = [];
                if (res.EMA_Gap_Pct !== undefined) {
                    let barsAgo = res.Crossover_Bars_Ago !== undefined ? res.Crossover_Bars_Ago : '?';
                    details.push(`<span style='color:#10b981; font-weight:bold; border:1px solid #10b981; padding:2px 4px; border-radius:4px; font-size:0.75rem;'>🔀 Kesişim ${barsAgo} saat önce | Fark: %${res.EMA_Gap_Pct}</span>`);
                }
                if (res.MACD_Match) details.push("<span style='color:#f59e0b'>MACD AL</span>");
                if (res.RSI_Match) details.push("<span style='color:#10b981'>RSI>50</span>");
                if (res.ADX_Match) details.push("<span style='color:#8b5cf6'>Güçlü Trend</span>");
                if (res.MOM_Match) details.push("<span style='color:#22c55e'>Momentum+</span>");
                
                tr.innerHTML = `
                    <td style="color:var(--text-main);font-weight:700;font-size:1.1rem;">${res.Symbol}</td>
                    <td style="font-family:monospace; font-weight:600;font-size:1.1rem;">${priceStr}</td>
                    <td style="color:${sColor};font-weight:700;font-size:1.1rem;">${s5} / 5</td>
                    <td style="font-size:0.85rem; line-height:1.4;">${details.join('<br>')}</td>
                    <td>${srCellHtml(res.Symbol, res.Price)}</td>
                `;
                opp1hTbody.appendChild(tr);
            });
        }
    }
}

// ========== SVR PROJECTIONS IMPLEMENTATION ==========
function bindSvrProjections(projections) {
    if (!projections) return;
    window.currentProjections = projections;
    
    // Default view: hourly
    toggleProjView('hourly');
    window.renderAdvancedChart();
}

function toggleProjView(mode) {
    if (!window.currentProjections) return;
    
    // Switch active buttons style
    const btnHourly = document.getElementById('btn-proj-hourly');
    const btnWeekly = document.getElementById('btn-proj-weekly');
    const btnMonthly = document.getElementById('btn-proj-monthly');
    
    [btnHourly, btnWeekly, btnMonthly].forEach(b => {
        if (b) {
            b.style.background = 'transparent';
            b.style.color = 'var(--text-muted)';
            b.style.border = '1px solid rgba(255,255,255,0.1)';
        }
    });
    
    const activeBtn = document.getElementById('btn-proj-' + mode);
    if (activeBtn) {
        activeBtn.style.background = 'rgba(147, 51, 234, 0.2)';
        activeBtn.style.color = 'var(--text-light)';
        activeBtn.style.border = '1px solid var(--accent-purple)';
    }
    
    // Render Hourly Table
    const hourlyTbody = document.getElementById('svr-hourly-body');
    const hData = window.currentProjections.Intraday_Hourly?.future_predicted || window.currentProjections.Intraday_Hourly?.data || window.currentProjections.Intraday_Hourly || [];
    const hMetrics = window.currentProjections.Intraday_Hourly?.metrics || {r2:0, rmse:0};
    
    if (hourlyTbody && hData.length > 0) {
        hourlyTbody.innerHTML = "";
        hData.forEach(item => {
            let tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${item.time}</td>
                <td style="color:var(--accent-red)">₺${item.min}</td>
                <td style="color:var(--text-light); font-weight:bold;">₺${item.expected}</td>
                <td style="color:var(--accent-green)">₺${item.max}</td>
            `;
            hourlyTbody.appendChild(tr);
        });
    }
    
    // Render Daily Table (Weekly or Monthly depending on mode)
    const dailyTbody = document.getElementById('svr-daily-body');
    let sourceObj = mode === 'monthly' ? window.currentProjections.Monthly_Daily : window.currentProjections.Weekly_Daily;
    const sourceData = sourceObj?.future_predicted || sourceObj?.data || sourceObj || [];
    const sourceMetrics = sourceObj?.metrics || {r2:0, rmse:0};
    
    if (dailyTbody && sourceData.length > 0) {
        dailyTbody.innerHTML = "";
        sourceData.forEach(item => {
            let tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${item.day}</td>
                <td style="color:var(--text-muted)">₺${item.expected_open}</td>
                <td style="color:var(--text-light); font-weight:bold;">₺${item.expected_close}</td>
                <td style="color:var(--accent-blue)">₺${item.min} - ₺${item.max}</td>
            `;
            dailyTbody.appendChild(tr);
        });
    }
    
    // Update Metrics Badges
    const activeMetrics = mode === 'hourly' ? hMetrics : sourceMetrics;
    const r2El = document.getElementById('svr-metric-r2');
    const rmseEl = document.getElementById('svr-metric-rmse');
    if(r2El) r2El.innerText = `R²: %${activeMetrics.r2 || "-"}`;
    if(rmseEl) rmseEl.innerText = `RMSE: ${activeMetrics.rmse || "-"}`;
    
    // Draw Chart
    updateSvrChart(mode);
}

function updateSvrChart(mode) {
    const ctx = document.getElementById('svrChart').getContext('2d');
    if (svrChartInstance) svrChartInstance.destroy();
    
    let sourceObj = mode === 'hourly' ? window.currentProjections?.Intraday_Hourly : (mode === 'monthly' ? window.currentProjections?.Monthly_Daily : window.currentProjections?.Weekly_Daily);
    if (!sourceObj) return;

    // Handle both new format (past/future) and old format (data) gracefully
    let pastReal = sourceObj.past_real || [];
    let pastPred = sourceObj.past_predicted || [];
    let futurePred = sourceObj.future_predicted || sourceObj.data || [];
    
    let isHourly = (mode === 'hourly');
    let titleText = isHourly ? "Saatlik Komite LSTM AI Tahmin Kanalları (Backtest + Gelecek)" : (mode === 'monthly' ? "Aylık (20 Günlük) LSTM AI Fiyat Projeksiyonu" : "Haftalık (5 Günlük) LSTM AI Fiyat Projeksiyonu");
    
    let labels = [];
    let realData = [];
    let svrData = [];
    
    // Geçmiş veriler
    for (let i = 0; i < pastReal.length; i++) {
        labels.push(isHourly ? pastReal[i].time : pastReal[i].day);
        realData.push(isHourly ? pastReal[i].expected : pastReal[i].expected_close);
        svrData.push(isHourly ? pastPred[i].expected : pastPred[i].expected_close);
    }
    
    // Gelecek veriler
    for (let i = 0; i < futurePred.length; i++) {
        labels.push(isHourly ? futurePred[i].time : futurePred[i].day);
        realData.push(null); // Gerçek fiyat gelecekte yok
        svrData.push(isHourly ? futurePred[i].expected : futurePred[i].expected_close);
    }
    
    svrChartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Gerçekleşen Fiyat (Geçmiş)',
                    data: realData,
                    borderColor: '#3b82f6',
                    backgroundColor: 'transparent',
                    borderWidth: 2,
                    pointRadius: 0,
                    tension: 0.1
                },
                {
                    label: 'LSTM AI Tahmin Rotası (Geçmiş + Gelecek)',
                    data: svrData,
                    borderColor: '#a855f7',
                    backgroundColor: 'transparent',
                    borderWidth: 2,
                    borderDash: [5, 5],
                    pointRadius: 0,
                    tension: 0.3
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: true, labels: { color: '#94a3b8', font: { size: 10 } } },
                title: { display: true, text: titleText, color: '#f8fafc', font: { size: 13, weight: 'bold' } }
            },
            scales: {
                x: { grid: { color: 'rgba(255, 255, 255, 0.05)' }, ticks: { color: '#64748b' } },
                y: { grid: { color: 'rgba(255, 255, 255, 0.05)' }, ticks: { color: '#64748b' } }
            }
        }
    });
}

// ========================================================
// 📱 MOBİL KART NAVİGASYONU (GERİ / İLERİ & KAYDIRMA)
// ========================================================
let currentCardIndex = 0;
const totalCards = 6;

function jumpToCard(cardIdx) {
    if (cardIdx < 0) cardIdx = 0;
    if (cardIdx >= totalCards) cardIdx = totalCards - 1;
    currentCardIndex = cardIdx;
    
    // Slider Butonlarını Güncelle
    const indicators = document.querySelectorAll('#slider-indicators .indicator-dot');
    indicators.forEach((dot, idx) => {
        if (idx === cardIdx) {
            dot.classList.add('active');
            try { dot.scrollIntoView({ behavior: 'smooth', inline: 'center', block: 'nearest' }); } catch(e){}
        } else {
            dot.classList.remove('active');
        }
    });

    // Alt Mobil Bar Butonlarını Güncelle
    const bms = ['bm-tavan', 'bm-1h', 'bm-5m'];
    bms.forEach((id, idx) => {
        const el = document.getElementById(id);
        if (el) {
            if (idx === cardIdx) el.classList.add('active');
            else el.classList.remove('active');
        }
    });

    // Hedef Karta Yumuşak Kaydır
    const targetCard = document.getElementById(`radar-card-${cardIdx}`);
    if (targetCard) {
        targetCard.scrollIntoView({ behavior: 'smooth', block: 'center' });
        targetCard.style.transition = 'box-shadow 0.4s ease, border-color 0.4s ease';
        const origBorder = targetCard.style.borderColor;
        targetCard.style.borderColor = '#38bdf8';
        targetCard.style.boxShadow = '0 0 25px rgba(56, 189, 248, 0.45)';
        setTimeout(() => {
            targetCard.style.borderColor = origBorder;
            targetCard.style.boxShadow = '';
        }, 1400);
    }
}

function navigateCard(direction) {
    let nextIdx = currentCardIndex + direction;
    if (nextIdx < 0) nextIdx = totalCards - 1;
    if (nextIdx >= totalCards) nextIdx = 0;
    jumpToCard(nextIdx);
}

// ==========================================
// 🚀 ALTIN VARANT SİMÜLATÖRÜ & GREEKS JS ENGINE
// ==========================================

async function runVarantSimulation() {
    const symSelect = document.getElementById('sim-symbol-select');
    const symbol = symSelect ? symSelect.value : 'THYAO';
    const issuerSelect = document.getElementById('sim-issuer-select');
    const issuer = issuerSelect ? issuerSelect.value : 'ALL';
    const resBox = document.getElementById('sim-result-box');
    if (!resBox) return;

    resBox.innerHTML = `<div style="text-align:center; padding:1rem; color:var(--text-muted);"><div class="spinner small" style="display:inline-block; margin-right:8px;"></div> ${issuer !== 'ALL' ? issuer + ' ' : ''}Varantları ve Black-Scholes kâr hesabı yapılıyor...</div>`;

    try {
        const response = await fetch(`/api/varant_simulator?symbol=${symbol}&issuer=${encodeURIComponent(issuer)}&t=${Date.now()}`);
        const data = await response.json();
        
        if (data.status === 'success' && data.warrants && data.warrants.length > 0) {
            let html = `<div style="display:flex; flex-direction:column; gap:0.6rem;">`;
            data.warrants.forEach(w => {
                let badgeColor = w.type === 'CALL' ? 'var(--accent-green)' : 'var(--accent-red)';
                let badgeBg = w.type === 'CALL' ? 'rgba(16,185,129,0.15)' : 'rgba(239,68,68,0.15)';
                let riskColor = w.risk_badge.includes('DÜŞÜK') ? 'var(--accent-green)' : 'var(--accent-yellow)';
                
                html += `
                <div style="background:rgba(255,255,255,0.03); border:1px solid var(--border-color); border-radius:8px; padding:0.6rem; display:flex; justify-content:space-between; align-items:center;">
                    <div>
                        <div style="display:flex; align-items:center; gap:6px;">
                            <span style="font-weight:800; color:var(--text-light); font-size:0.95rem;">${w.code}</span>
                            <span style="background:${badgeBg}; color:${badgeColor}; font-size:0.7rem; font-weight:bold; padding:2px 6px; border-radius:4px;">${w.type}</span>
                            <span style="font-size:0.72rem; color:var(--accent-yellow); font-weight:600;">🏛️ ${w.issuer}</span>
                            <span style="font-size:0.72rem; color:var(--text-muted);">Vade: ${w.maturity_days}G</span>
                        </div>
                        <div style="font-size:0.75rem; color:var(--text-muted); margin-top:2px;">
                            Giriş: <b>${w.current_warrant_price}</b> | Hedef: <b style="color:var(--accent-green);">${w.target_warrant_price}</b> | Kaldıraç: <b>${w.gearing}</b> | Δ: <b>${w.delta}</b>
                        </div>
                    </div>
                    <div style="text-align:right;">
                        <div style="font-size:1.05rem; font-weight:800; color:var(--accent-green);">${w.warrant_gain_pct}</div>
                        <div style="font-size:0.7rem; color:${riskColor};">${w.risk_badge}</div>
                    </div>
                </div>
                `;
            });
            html += `</div>`;
            resBox.innerHTML = html;
        } else {
            resBox.innerHTML = `<div style="text-align:center; padding:1rem; color:var(--text-muted);">Bu hisse ve seçilen kurum (${issuer}) için aktif varant bulunamadı.</div>`;
        }
    } catch (e) {
        resBox.innerHTML = `<div style="text-align:center; padding:1rem; color:var(--accent-red);">Simülasyon yüklenirken hata: ${e.message}</div>`;
    }
}

async function fetchWinRateScorecard() {
    try {
        const res = await fetch(`/api/winrate_stats?t=${Date.now()}`);
        const data = await res.json();
        if (data.status === 'success' && data.stats) {
            const s = data.stats.summary;
            renderSimulationPerformance(data.trade_performance || {}, 'scorecard-trade-performance');
            setElText('stat-winrate', `%${s.win_rate_pct}`);
            setElText('stat-avgprofit', `+%${s.avg_profit_pct}`);
            setElText('stat-pfactor', s.profit_factor);

            setElText('dt-stat-total', s.total_signals_30d);
            setElText('dt-stat-win', `%${s.win_rate_pct}`);
            setElText('dt-stat-duration', s.avg_time_to_target_hours);

            // Populate history table in Detailed Analysis
            const tbody = document.getElementById('dt-winrate-history-tbody');
            if (tbody && data.stats.recent_completed_signals) {
                tbody.innerHTML = '';
                data.stats.recent_completed_signals.forEach(item => {
                    let tr = document.createElement('tr');
                    let statusColor = item.pnl_pct.includes('+') ? 'var(--accent-green)' : 'var(--accent-red)';
                    let warrantColor = item.warrant_gain.includes('+') ? 'var(--accent-green)' : 'var(--accent-red)';
                    
                    tr.innerHTML = `
                        <td style="font-weight:bold; color:var(--text-light);">${item.symbol}</td>
                        <td style="color:var(--text-muted); font-size:0.8rem;">${item.date}</td>
                        <td><span class="badge" style="background:rgba(255,255,255,0.05); font-size:0.75rem;">${item.signal_type}</span></td>
                        <td>${item.entry_price}</td>
                        <td style="color:var(--accent-blue);">${item.target_price}</td>
                        <td style="font-weight:bold;">${item.exit_price}</td>
                        <td style="color:${statusColor}; font-weight:bold;">${item.pnl_pct}</td>
                        <td style="color:${warrantColor}; font-weight:800;">${item.warrant_gain}</td>
                        <td style="color:var(--text-muted); font-size:0.8rem;">${item.duration}</td>
                        <td><span style="color:${statusColor}; font-size:0.75rem; font-weight:bold;">${item.status}</span></td>
                    `;
                    tbody.appendChild(tr);
                });
            }
        }
    } catch (e) {
        console.error("Winrate Scorecard yükleme hatası:", e);
    }
}

async function loadDetailedVarantSim(symbol, spotPrice) {
    const spotEl = document.getElementById('dt-sim-spot');
    const targetInput = document.getElementById('dt-sim-target-input');
    const issuerSelect = document.getElementById('dt-sim-issuer-select');
    const issuer = issuerSelect ? issuerSelect.value : 'ALL';
    const tbody = document.getElementById('dt-varantsim-tbody');
    
    if (spotEl) spotEl.innerText = `₺${parseFloat(spotPrice || 100).toFixed(2)}`;
    let defaultTarget = roundTo(parseFloat(spotPrice || 100) * 1.099, 2);
    if (targetInput) targetInput.value = defaultTarget;

    if (!tbody) return;
    tbody.innerHTML = `<tr><td colspan="10" class="text-muted text-center" style="padding:2rem;"><div class="spinner small" style="display:inline-block; margin-right:8px;"></div> ${issuer !== 'ALL' ? issuer + ' ' : ''}Varantları ve Greeks matrisi hesaplanıyor...</td></tr>`;

    try {
        const cleanSym = symbol.replace('.IS', '').toUpperCase();
        const response = await fetch(`/api/varant_simulator?symbol=${cleanSym}&price=${spotPrice}&target=${defaultTarget}&issuer=${encodeURIComponent(issuer)}&t=${Date.now()}`);
        const data = await response.json();

        if (data.status === 'success' && data.warrants && data.warrants.length > 0) {
            tbody.innerHTML = '';
            data.warrants.forEach(w => {
                let tr = document.createElement('tr');
                let badgeColor = w.type === 'CALL' ? 'var(--accent-green)' : 'var(--accent-red)';
                let riskColor = w.risk_badge.includes('DÜŞÜK') ? 'var(--accent-green)' : 'var(--accent-yellow)';
                
                tr.innerHTML = `
                    <td style="font-weight:800; color:var(--text-light); font-size:0.95rem;">${w.code}</td>
                    <td><span style="color:${badgeColor}; font-weight:bold;">${w.type}</span> <span style="font-size:0.75rem; color:var(--accent-yellow); font-weight:600;">(🏛️ ${w.issuer})</span></td>
                    <td style="font-weight:bold;">${w.current_warrant_price}</td>
                    <td style="color:var(--accent-green); font-weight:bold;">${w.target_warrant_price}</td>
                    <td style="color:var(--accent-blue);">${w.spot_gain_pct}</td>
                    <td style="color:var(--accent-green); font-weight:800; font-size:0.95rem;">${w.warrant_gain_pct}</td>
                    <td><span style="color:var(--accent-purple); font-weight:bold;">Δ ${w.delta}</span> <span style="font-size:0.75rem; color:var(--text-muted);">(${w.gearing})</span></td>
                    <td style="color:var(--accent-red); font-size:0.8rem;">${w.theta}</td>
                    <td style="color:var(--accent-yellow); font-size:0.8rem;">${w.weekend_decay}</td>
                    <td><span style="color:${riskColor}; font-size:0.75rem; font-weight:bold;">${w.risk_badge}</span></td>
                `;
                tbody.appendChild(tr);
            });
        } else {
            tbody.innerHTML = `<tr><td colspan="10" class="text-muted text-center" style="padding:2rem;">Bu hisse ve seçilen kurum (${issuer}) için aktif ihraç edilmiş varant bulunmamaktadır.</td></tr>`;
        }
    } catch (e) {
        tbody.innerHTML = `<tr><td colspan="10" class="text-red text-center" style="padding:2rem;">Hesaplama hatası: ${e.message}</td></tr>`;
    }
}

async function recalculateDetailVarantSim() {
    const sym = window.currentAnalyzedSymbol || document.getElementById('tk-sym')?.innerText || 'THYAO';
    const spot = parseFloat(document.getElementById('tk-price')?.innerText?.replace('₺','').replace(',','') || 100);
    const targetInput = document.getElementById('dt-sim-target-input');
    const targetVal = parseFloat(targetInput?.value || spot * 1.099);
    const issuerSelect = document.getElementById('dt-sim-issuer-select');
    const issuer = issuerSelect ? issuerSelect.value : 'ALL';
    
    const tbody = document.getElementById('dt-varantsim-tbody');
    if (tbody) tbody.innerHTML = `<tr><td colspan="10" class="text-muted text-center" style="padding:2rem;"><div class="spinner small" style="display:inline-block; margin-right:8px;"></div> Yeniden hesaplanıyor (${issuer})...</td></tr>`;

    try {
        const cleanSym = sym.replace('.IS', '').toUpperCase();
        const response = await fetch(`/api/varant_simulator?symbol=${cleanSym}&price=${spot}&target=${targetVal}&issuer=${encodeURIComponent(issuer)}&t=${Date.now()}`);
        const data = await response.json();

        if (data.status === 'success' && data.warrants && data.warrants.length > 0) {
            tbody.innerHTML = '';
            data.warrants.forEach(w => {
                let tr = document.createElement('tr');
                let badgeColor = w.type === 'CALL' ? 'var(--accent-green)' : 'var(--accent-red)';
                let riskColor = w.risk_badge.includes('DÜŞÜK') ? 'var(--accent-green)' : 'var(--accent-yellow)';
                
                tr.innerHTML = `
                    <td style="font-weight:800; color:var(--text-light); font-size:0.95rem;">${w.code}</td>
                    <td><span style="color:${badgeColor}; font-weight:bold;">${w.type}</span> <span style="font-size:0.75rem; color:var(--accent-yellow); font-weight:600;">(🏛️ ${w.issuer})</span></td>
                    <td style="font-weight:bold;">${w.current_warrant_price}</td>
                    <td style="color:var(--accent-green); font-weight:bold;">${w.target_warrant_price}</td>
                    <td style="color:var(--accent-blue);">${w.spot_gain_pct}</td>
                    <td style="color:var(--accent-green); font-weight:800; font-size:0.95rem;">${w.warrant_gain_pct}</td>
                    <td><span style="color:var(--accent-purple); font-weight:bold;">Δ ${w.delta}</span> <span style="font-size:0.75rem; color:var(--text-muted);">(${w.gearing})</span></td>
                    <td style="color:var(--accent-red); font-size:0.8rem;">${w.theta}</td>
                    <td style="color:var(--accent-yellow); font-size:0.8rem;">${w.weekend_decay}</td>
                    <td><span style="color:${riskColor}; font-size:0.75rem; font-weight:bold;">${w.risk_badge}</span></td>
                `;
                tbody.appendChild(tr);
            });
        } else {
            tbody.innerHTML = `<tr><td colspan="10" class="text-muted text-center" style="padding:2rem;">Bu hisse ve seçilen kurum (${issuer}) için aktif ihraç edilmiş varant bulunmamaktadır.</td></tr>`;
        }
    } catch (e) {
        console.error("Varant Sim Recalculate Error:", e);
    }
}

// Sayfa yüklendiğinde simülatörü ve sinyal karnesini otomatik yükle
window.addEventListener('DOMContentLoaded', () => {
    fetchWinRateScorecard();
    runVarantSimulation();
    fetchHomeWinrateStats();
    fetchStatsTabData();
});

// 📸 ANALİZ RAPORUNU JPG / GÖRSEL OLARAK İNDİRME FONKSİYONU
async function exportAnalysisAsJPG() {
    const sym = window.currentAnalyzedSymbol || document.getElementById('tk-sym')?.innerText || 'ANALIZ';
    const targetElement = document.getElementById('dashboard-wrapper');
    const btn = document.getElementById('btn-export-jpg');
    
    if (!targetElement) return;
    
    if (typeof html2canvas === 'undefined') {
        alert('Görsel kütüphanesi yüklenemedi. Lütfen sayfayı yenileyiniz.');
        return;
    }
    
    const originalBtnText = btn ? btn.innerHTML : '';
    if (btn) {
        btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Hazırlanıyor...';
        btn.disabled = true;
    }
    
    try {
        const canvas = await html2canvas(targetElement, {
            backgroundColor: '#131314',
            scale: 2, // Yüksek çözünürlüklü Retina/HD çıktı
            useCORS: true,
            logging: false,
            windowWidth: targetElement.scrollWidth,
            windowHeight: targetElement.scrollHeight
        });
        
        // JPG / PNG İndirici Linki
        const imageURL = canvas.toDataURL('image/jpeg', 0.95);
        const downloadLink = document.createElement('a');
        const nowStr = new Date().toISOString().slice(0,10);
        downloadLink.download = `VarantRadar_${sym}_Analiz_${nowStr}.jpg`;
        downloadLink.href = imageURL;
        document.body.appendChild(downloadLink);
        downloadLink.click();
        document.body.removeChild(downloadLink);
    } catch (err) {
        console.error("JPG Export Error:", err);
        alert("Görsel oluşturulurken bir hata oluştu: " + err.message);
    } finally {
        if (btn) {
            btn.innerHTML = originalBtnText;
            btn.disabled = false;
        }
    }
}

// 📱 MOBİL & MASAÜSTÜ KATEGORİ FİLTRELEME FONKSİYONU (PILL TABS)
function filterRadarGrid(targetCardId, btnElement) {
    const allCards = document.querySelectorAll('#radar-cards-grid > .card');
    const allPillBtns = document.querySelectorAll('#radar-pill-tabs .pill-btn');
    
    // Update pill active states
    allPillBtns.forEach(b => {
        b.classList.remove('active');
        b.style.background = 'rgba(30,41,59,0.8)';
        b.style.color = 'var(--text-muted)';
        b.style.borderColor = 'rgba(255,255,255,0.1)';
    });
    
    if (btnElement) {
        btnElement.classList.add('active');
        btnElement.style.background = 'linear-gradient(135deg, rgba(59, 130, 246, 0.3) 0%, rgba(37, 99, 235, 0.3) 100%)';
        btnElement.style.color = '#38bdf8';
        btnElement.style.borderColor = '#38bdf8';
    }
    
    if (targetCardId === 'all') {
        allCards.forEach(c => {
            c.style.display = 'block';
            c.classList.add('card-fade-in');
        });
    } else {
        allCards.forEach(c => {
            if (c.id === targetCardId) {
                c.style.display = 'block';
                c.classList.add('card-fade-in');
                // Mobilde yumusak kaydirma
                if (window.innerWidth <= 850) {
                    c.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                }
            } else {
                c.style.display = 'none';
            }
        });
    }
}

// 📱 MOBİL SWIPE KALDIRILDI — Tablolar serbest yatay kaydırılabilir

// ================================================================
// 📊 10:15 SABAH TAVAN LİSTESİ & 18:10 SEANS KAPANIŞ KARNESİ JS
// ================================================================

function openTavanAuditModal(skipFetch = false) {
    const modal = document.getElementById('tavan-audit-modal');
    if (modal) {
        modal.style.display = 'block';
        document.body.style.overflow = 'hidden';
        if (!skipFetch) {
            fetchTavanAuditData();
        }
    }
}

function closeTavanAuditModal() {
    const modal = document.getElementById('tavan-audit-modal');
    if (modal) {
        modal.style.display = 'none';
        document.body.style.overflow = 'auto';
    }
}

// ESC tuşuna basınca veya modal dışına tıklayınca kapatma
window.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeTavanAuditModal();
});
window.addEventListener('click', (e) => {
    const modal = document.getElementById('tavan-audit-modal');
    if (e.target === modal) closeTavanAuditModal();
});

async function fetchTavanAuditData(dateStr = '') {
    const tbody = document.getElementById('tavan-audit-tbody');
    const dateSelect = document.getElementById('tavan-audit-date-select');
    
    if (tbody) {
        tbody.innerHTML = `<tr><td colspan="10" class="text-muted text-center" style="padding:2rem;"><div class="spinner small" style="display:inline-block; margin-right:8px;"></div> 10:15 Sabah Adayları & 18:10 Kapanış Denetimi yükleniyor...</td></tr>`;
    }

    try {
        const url = dateStr ? `/api/tavan_tracker?date=${encodeURIComponent(dateStr)}` : '/api/tavan_tracker';
        const res = await fetch(url);
        const data = await res.json();

        if (data.status === 'success' && data.audit) {
            const audit = data.audit;
            const summary = audit.summary || {};
            const items = audit.items || [];
            const overall = data.overall_stats || {};

            // 1. Tarih Seçiciyi Doldur
            if (dateSelect && data.available_dates) {
                dateSelect.innerHTML = '';
                data.available_dates.forEach(d => {
                    const opt = document.createElement('option');
                    opt.value = d;
                    opt.innerText = (d === new Date().toISOString().slice(0, 10)) ? `📅 Bugün (${d})` : `📅 ${d}`;
                    if (d === data.selected_date) opt.selected = true;
                    dateSelect.appendChild(opt);
                });
            }

            // 2. Durum Rozeti
            const isCompleted = audit.status === 'COMPLETED';
            const badgeEl = document.getElementById('tavan-audit-status-badge');
            if (badgeEl) {
                badgeEl.style.background = isCompleted ? 'rgba(16,185,129,0.2)' : 'rgba(56,189,248,0.2)';
                badgeEl.style.color = isCompleted ? '#10b981' : '#38bdf8';
                badgeEl.style.borderColor = isCompleted ? 'rgba(16,185,129,0.4)' : 'rgba(56,189,248,0.4)';
                badgeEl.innerHTML = isCompleted ? '<i class="fa-solid fa-check-double"></i> 18:10 KAPANIŞ DENETİMİ TAMAMLANDI' : '<i class="fa-solid fa-circle-notch fa-spin"></i> SEANS SÜRÜYOR (CANLI TAKİP)';
            }

            const evalTimeEl = document.getElementById('tavan-audit-eval-time');
            if (evalTimeEl) {
                evalTimeEl.innerText = `Kayıt: ${audit.snapshot_time || '10:15'} | Denetim: ${audit.evaluation_time || '18:10'}`;
            }

            // 3. Kümülatif Başarı Barı
            const cumBanner = document.getElementById('tavan-audit-cum-banner');
            if (cumBanner && overall) {
                cumBanner.innerHTML = `🎯 <b>30 Günlük Kümülatif:</b> 10:15 Tavan Adaylarının <span style="color:#10b981; font-weight:800;">%${overall.cumulative_tavan_success_pct}'i Tavana</span>, <span style="color:#facc15; font-weight:800;">%${overall.cumulative_plus5_success_pct}'i +%5 Üzeri Kazanca</span> ulaştı. (Ort. Max: +%${overall.cumulative_avg_max_gain_pct})`;
            }

            // 4. KPI Kartları
            const totalCnt = summary.total_candidates || items.length || 0;
            const tavanCnt = summary.hit_ceiling_count || 0;
            const tavanPct = summary.hit_ceiling_pct || 0;
            const plus5Cnt = summary.hit_plus5_count || 0;
            const plus5Pct = summary.hit_plus5_pct || 0;
            const avgMax = summary.avg_max_gain_pct || 0.0;
            const avgClose = summary.avg_closing_gain_pct || 0.0;
            const avgWarrant = (avgMax * 6.2).toFixed(1);

            setElText('aud-total-cnt', `${totalCnt} Hisse`);
            setElText('aud-tavan-cnt', `${tavanCnt} / ${totalCnt} (%${tavanPct})`);
            setElText('aud-plus5-cnt', `${plus5Cnt} / ${totalCnt} (%${plus5Pct})`);
            setElText('aud-avg-max', `+%${avgMax}`);
            setElText('aud-avg-close', `+%${avgClose}`);
            setElText('aud-warrant-avg', `+%${avgWarrant}`);

            // 5. Tablo Satırları
            if (tbody) {
                if (items.length === 0) {
                    tbody.innerHTML = `<tr><td colspan="10" class="text-muted text-center" style="padding:2rem;">Bu tarihe ait 10:15 tavan adayı kaydı bulunmamaktadır.</td></tr>`;
                    return;
                }

                tbody.innerHTML = '';
                items.forEach(it => {
                    const tr = document.createElement('tr');
                    const isTavan = it.hit_ceiling;
                    const isPlus5 = it.hit_plus5;
                    
                    let badgeBg = 'rgba(255,255,255,0.05)';
                    let badgeColor = 'var(--text-muted)';
                    if (isTavan) {
                        badgeBg = 'rgba(16,185,129,0.2)';
                        badgeColor = '#10b981';
                    } else if (isPlus5) {
                        badgeBg = 'rgba(56,189,248,0.2)';
                        badgeColor = '#38bdf8';
                    } else if (it.max_gain_pct > 0) {
                        badgeBg = 'rgba(234,179,8,0.2)';
                        badgeColor = '#facc15';
                    } else {
                        badgeBg = 'rgba(239,68,68,0.2)';
                        badgeColor = '#ef4444';
                    }
                    
                    if (it.stop_loss_triggered) {
                        badgeBg = 'rgba(239,68,68,0.4)';
                        badgeColor = '#ef4444';
                    }

                    const closeGainSign = it.closing_gain_pct >= 0 ? '+' : '';
                    const maxGainSign = it.max_gain_pct >= 0 ? '+' : '';
                    const closeGainCol = it.closing_gain_pct >= 5 ? '#38bdf8' : (it.closing_gain_pct >= 0 ? '#10b981' : '#ef4444');
                    const maxGainCol = it.max_gain_pct >= 9 ? '#10b981' : (it.max_gain_pct >= 5 ? '#38bdf8' : '#facc15');

                    tr.innerHTML = `
                        <td>
                            <div style="font-weight:800; color:var(--text-light); font-size:0.95rem;">${it.symbol}</div>
                            <div style="font-size:0.7rem; color:var(--accent-yellow); font-weight:600;">${it.morning_phase || 'GİRİŞ'} (Puan: ${it.morning_score})</div>
                        </td>
                        <td style="font-weight:bold; color:#fff;">₺${parseFloat(it.morning_price).toFixed(2)}</td>
                        <td style="color:var(--accent-red); font-weight:bold;">₺${parseFloat(it.ceiling_target).toFixed(2)} <span style="font-size:0.72rem; color:var(--text-muted);">(${it.distance_to_ceiling_1015})</span></td>
                        <td style="color:#facc15; font-weight:800;">₺${parseFloat(it.daily_high).toFixed(2)}</td>
                        <td style="font-weight:bold; color:var(--text-light);">₺${parseFloat(it.closing_price).toFixed(2)}</td>
                        <td style="color:${closeGainCol}; font-weight:bold;">${closeGainSign}%${parseFloat(it.closing_gain_pct).toFixed(2)}</td>
                        <td style="color:${maxGainCol}; font-weight:800; font-size:0.95rem;">${maxGainSign}%${parseFloat(it.max_gain_pct).toFixed(2)}</td>
                        <td>
                            <span style="background:${badgeBg}; color:${badgeColor}; border:1px solid ${badgeColor}; padding:3px 8px; border-radius:6px; font-weight:700; font-size:0.75rem; white-space:nowrap; ${it.stop_loss_triggered ? 'animation: pulse 1.5s infinite;' : ''}">
                                ${it.result_badge}
                            </span>
                        </td>
                        <td>
                            <div style="font-weight:800; color:#c084fc; font-size:0.85rem;">🏛️ ${it.ahlatci_warrant}</div>
                            <div style="font-size:0.72rem; color:#10b981; font-weight:700;">${it.warrant_gain_pct} <span style="color:var(--text-muted); font-size:0.68rem;">(${it.warrant_leverage})</span></div>
                        </td>
                        <td>
                            <button onclick="closeTavanAuditModal(); analyzeSymbol('${it.symbol}')" class="btn-primary" style="padding:3px 8px; font-size:0.75rem;" title="Hisse Analizini Aç">İncele</button>
                        </td>
                    `;
                    tbody.appendChild(tr);
                });
            }
        } else {
            if (tbody) tbody.innerHTML = `<tr><td colspan="10" class="text-red text-center" style="padding:2rem;">Denetim verisi alınamadı.</td></tr>`;
        }
    } catch (e) {
        if (tbody) tbody.innerHTML = `<tr><td colspan="10" class="text-red text-center" style="padding:2rem;">Bağlantı hatası: ${e.message}</td></tr>`;
    }
// ==========================================
// 🏆 UZUN VADELİ TAVAN & +%5 KÂR ARŞİVİ KONTROLCÜSÜ (05 AĞUSTOS 2026'DAN İTİBAREN)
// ==========================================
}

function openLongTermHistoryModal() {
    // Redirect to the new stats tab layout
    const statsBtn = document.querySelector('.nav-btn[onclick*="stats"]');
    if (statsBtn) {
        switchMainTab('stats', statsBtn);
    }
}

function closeLongTermHistoryModal() {
    // No-op, old modal is removed.
}

function applyLongTermFilter() {
    const startDate = document.getElementById('hist-start-date')?.value || '2026-08-04';
    const endDate = document.getElementById('hist-end-date')?.value || '';
    const symbol = document.getElementById('hist-symbol-search')?.value || '';
    const time = document.getElementById('hist-time-filter')?.value || '';
    fetchLongTermHistoryData(startDate, endDate, symbol, time);
}

function openTavanAuditForDate(dateStr) {
    try {
        console.log("Opening Tavan Audit Modal for date:", dateStr);
        const modal = document.getElementById('tavan-audit-modal');
        if (modal) {
            modal.style.display = 'block';
            modal.style.zIndex = '9999999'; // Ensure it's on top
            document.body.style.overflow = 'hidden';
            
            // Show loading immediately
            const tbody = document.getElementById('tavan-audit-tbody');
            if (tbody) {
                tbody.innerHTML = `<tr><td colspan="10" class="text-muted text-center" style="padding:2rem;"><i class="fa-solid fa-spinner fa-spin"></i> ${dateStr} verileri yükleniyor...</td></tr>`;
            }
            
            const select = document.getElementById('tavan-audit-date-select');
            if (select) {
                // Ensure the option exists before setting
                let optionExists = Array.from(select.options).some(opt => opt.value === dateStr);
                if (!optionExists) {
                    const opt = document.createElement('option');
                    opt.value = dateStr;
                    opt.textContent = dateStr;
                    select.appendChild(opt);
                }
                select.value = dateStr;
            }
            fetchTavanAuditData(dateStr);
        } else {
            console.error("tavan-audit-modal element not found in DOM!");
            alert("Sistem Hatası: Denetim penceresi bulunamadı.");
        }
    } catch(e) {
        console.error("Error opening audit modal:", e);
        alert("Hata: " + e.message);
    }
}

// ============================================================
// 📊 İSTATİSTİKLER SEKMESİ - ANA FONKSİYONLARI
// ============================================================

let global_stats_data = null;


let current_stats_mode = 'daily';

function switchStatsMode(mode) {
    current_stats_mode = mode;
    const dailyBtn = document.getElementById('stats-mode-daily-btn');
    const cumBtn = document.getElementById('stats-mode-cumulative-btn');
    if(!dailyBtn || !cumBtn) return;
    if (mode === 'daily') {
        dailyBtn.style.background = 'var(--accent-purple)';
        dailyBtn.style.color = '#fff';
        cumBtn.style.background = 'transparent';
        cumBtn.style.color = 'var(--text-muted)';
    } else {
        cumBtn.style.background = 'var(--accent-purple)';
        cumBtn.style.color = '#fff';
        dailyBtn.style.background = 'transparent';
        dailyBtn.style.color = 'var(--text-muted)';
    }
    renderStatsMode();
}

function renderStatsMode() {
    if (typeof global_stats_data === 'undefined' || !global_stats_data) return;
    const data = global_stats_data;
    const el = (id) => document.getElementById(id);
    
    if (current_stats_mode === 'cumulative') {
        const summ = data.summary || {};
        if (el('stats-tab-total-days')) el('stats-tab-total-days').innerText = summ.total_days_tracked || 0;
        if (el('stats-tab-total-candidates-sub')) el('stats-tab-total-candidates-sub').innerText = `Toplam ${summ.total_candidates_tracked || 0} Öneri`;
        if (el('stats-tab-tavan-rate')) el('stats-tab-tavan-rate').innerText = `%${summ.tavan_success_pct || 0}`;
        if (el('stats-tab-tavan-cnt-sub')) el('stats-tab-tavan-cnt-sub').innerText = `${summ.total_hit_ceiling || 0} Tavan`;
        if (el('stats-tab-plus5-rate')) el('stats-tab-plus5-rate').innerText = `%${summ.plus5_success_pct || 0}`;
        if (el('stats-tab-plus5-cnt-sub')) el('stats-tab-plus5-cnt-sub').innerText = `${summ.total_hit_plus5 || 0} Hisse`;
        if (el('stats-tab-avg-max-gain')) el('stats-tab-avg-max-gain').innerText = `+ %${(summ.cumulative_avg_max_gain_pct || 0).toFixed(2)}`;
        if (el('stats-tab-avg-close-sub')) el('stats-tab-avg-close-sub').innerText = `Kapanış: %${(summ.cumulative_avg_closing_gain_pct || 0).toFixed(2)}`;
        if (el('stats-tab-warrant-avg-gain')) el('stats-tab-warrant-avg-gain').innerText = `+ %${(summ.ahlatci_warrant_avg_gain_pct || 0).toFixed(2)}`;
        if (el('stats-tab-pos-count')) el('stats-tab-pos-count').innerText = `${summ.total_closed_positive || summ.total_hit_plus5 || 0} Adet`;
        if (el('stats-tab-pos-avg')) el('stats-tab-pos-avg').innerText = `(Ort. +%${(summ.avg_positive_close_gain || summ.cumulative_avg_max_gain_pct || 0).toFixed(2)})`;
        if (el('stats-tab-neg-count')) el('stats-tab-neg-count').innerText = `${summ.total_closed_negative || ((summ.total_candidates_tracked || 0) - (summ.total_hit_plus5 || 0))} Adet`;
        if (el('stats-tab-neg-avg')) el('stats-tab-neg-avg').innerText = `(Ort. %${Math.abs(summ.avg_negative_close_gain || 0).toFixed(2)})`;
        let netPct = summ.net_profit_pct || summ.cumulative_avg_closing_gain_pct || 0;
        let netSign = netPct > 0 ? '+' : '';
        if (el('stats-tab-net-pct')) el('stats-tab-net-pct').innerText = `${netSign}%${netPct.toFixed(2)}`;
        let netCard = el('stats-tab-net-card');
        if (netCard) {
            if (netPct > 0) {
                netCard.style.background = 'linear-gradient(145deg, rgba(16,185,129,0.05) 0%, rgba(15,23,42,1) 100%)';
                netCard.style.border = '1px solid rgba(16,185,129,0.2)';
                if (el('stats-tab-net-pct')) el('stats-tab-net-pct').style.color = 'var(--accent-green)';
            } else if (netPct < 0) {
                netCard.style.background = 'linear-gradient(145deg, rgba(239,68,68,0.05) 0%, rgba(15,23,42,1) 100%)';
                netCard.style.border = '1px solid rgba(239,68,68,0.2)';
                if (el('stats-tab-net-pct')) el('stats-tab-net-pct').style.color = 'var(--accent-red)';
            } else {
                netCard.style.background = 'linear-gradient(145deg, rgba(59,130,246,0.05) 0%, rgba(15,23,42,1) 100%)';
                netCard.style.border = '1px solid rgba(59,130,246,0.2)';
                if (el('stats-tab-net-pct')) el('stats-tab-net-pct').style.color = 'var(--text-muted)';
            }
        }
        if (el('stats-tab-elite-pos-count')) el('stats-tab-elite-pos-count').innerText = `${summ.elite_closed_positive || 0} Adet`;
        if (el('stats-tab-elite-pos-avg')) el('stats-tab-elite-pos-avg').innerText = `(Ort. +%${(summ.elite_avg_positive_gain || 0).toFixed(2)})`;
        if (el('stats-tab-elite-neg-count')) el('stats-tab-elite-neg-count').innerText = `${summ.elite_closed_negative || 0} Adet`;
        if (el('stats-tab-elite-neg-avg')) el('stats-tab-elite-neg-avg').innerText = `(Ort. %${Math.abs(summ.elite_avg_negative_gain || 0).toFixed(2)})`;
        let eliteNet = summ.elite_net_profit_pct || 0;
        let eliteSign = eliteNet > 0 ? '+' : '';
        if (el('stats-tab-elite-net-pct')) el('stats-tab-elite-net-pct').innerText = `${eliteSign}%${eliteNet.toFixed(2)}`;
        let eliteCard = el('stats-tab-elite-net-card');
        if (eliteCard) {
            if (eliteNet > 0) {
                eliteCard.style.background = 'linear-gradient(145deg, rgba(234,179,8,0.05) 0%, rgba(15,23,42,1) 100%)';
                eliteCard.style.border = '1px solid rgba(234,179,8,0.5)';
                if (el('stats-tab-elite-net-pct')) el('stats-tab-elite-net-pct').style.color = 'var(--accent-yellow)';
            } else {
                eliteCard.style.background = 'linear-gradient(145deg, rgba(239,68,68,0.05) 0%, rgba(15,23,42,1) 100%)';
                eliteCard.style.border = '1px solid rgba(239,68,68,0.5)';
                if (el('stats-tab-elite-net-pct')) el('stats-tab-elite-net-pct').style.color = 'var(--accent-red)';
            }
        }
    } else {
        const history = data.daily_breakdown || data.history || [];
        if (history.length > 0) {
            const today = history[0]; 
            const allSyms = today.all_symbols || [];
            const totalC = allSyms.length;
            const tavanC = allSyms.filter(s => s.hit_ceiling).length;
            const plus5C = allSyms.filter(s => s.hit_plus5).length;
            const posSyms = allSyms.filter(s => (s.closing_gain_pct || 0) > 0);
            const negSyms = allSyms.filter(s => (s.closing_gain_pct || 0) <= 0);
            const sumMax = allSyms.reduce((sum, s) => sum + (s.max_gain_pct || 0), 0);
            const sumClose = allSyms.reduce((sum, s) => sum + (s.closing_gain_pct || 0), 0);
            const avgMax = totalC > 0 ? sumMax / totalC : 0;
            const avgClose = totalC > 0 ? sumClose / totalC : 0;
            const posGain = posSyms.reduce((sum, s) => sum + (s.closing_gain_pct || 0), 0);
            const negGain = negSyms.reduce((sum, s) => sum + (s.closing_gain_pct || 0), 0);
            const avgPosGain = posSyms.length > 0 ? posGain / posSyms.length : 0;
            const avgNegGain = negSyms.length > 0 ? negGain / negSyms.length : 0;
            const elites = allSyms.filter(s => (s.morning_score || 0) >= 99.9);
            const elitesPos = elites.filter(s => (s.closing_gain_pct || 0) > 0);
            const elitesNeg = elites.filter(s => (s.closing_gain_pct || 0) <= 0);
            const elitePosGain = elitesPos.reduce((sum, s) => sum + (s.closing_gain_pct || 0), 0);
            const eliteNegGain = elitesNeg.reduce((sum, s) => sum + (s.closing_gain_pct || 0), 0);
            const avgElitePos = elitesPos.length > 0 ? elitePosGain / elitesPos.length : 0;
            const avgEliteNeg = elitesNeg.length > 0 ? eliteNegGain / elitesNeg.length : 0;
            const eliteNet = elites.length > 0 ? (elitePosGain + eliteNegGain) / elites.length : 0;
            if (el('stats-tab-total-days')) el('stats-tab-total-days').innerText = today.date || 'Bugün';
            if (el('stats-tab-total-candidates-sub')) el('stats-tab-total-candidates-sub').innerText = `Toplam ${totalC} Öneri`;
            if (el('stats-tab-tavan-rate')) el('stats-tab-tavan-rate').innerText = `%${totalC > 0 ? (tavanC/totalC*100).toFixed(1) : 0}`;
            if (el('stats-tab-tavan-cnt-sub')) el('stats-tab-tavan-cnt-sub').innerText = `${tavanC} Tavan`;
            if (el('stats-tab-plus5-rate')) el('stats-tab-plus5-rate').innerText = `%${totalC > 0 ? (plus5C/totalC*100).toFixed(1) : 0}`;
            if (el('stats-tab-plus5-cnt-sub')) el('stats-tab-plus5-cnt-sub').innerText = `${plus5C} Hisse`;
            if (el('stats-tab-avg-max-gain')) el('stats-tab-avg-max-gain').innerText = `+ %${avgMax.toFixed(2)}`;
            if (el('stats-tab-avg-close-sub')) el('stats-tab-avg-close-sub').innerText = `Kapanış: %${avgClose.toFixed(2)}`;
            if (el('stats-tab-warrant-avg-gain')) el('stats-tab-warrant-avg-gain').innerText = `+ %${(avgMax * 6.2).toFixed(2)}`;
            if (el('stats-tab-pos-count')) el('stats-tab-pos-count').innerText = `${posSyms.length} Adet`;
            if (el('stats-tab-pos-avg')) el('stats-tab-pos-avg').innerText = `(Ort. +%${avgPosGain.toFixed(2)})`;
            if (el('stats-tab-neg-count')) el('stats-tab-neg-count').innerText = `${negSyms.length} Adet`;
            if (el('stats-tab-neg-avg')) el('stats-tab-neg-avg').innerText = `(Ort. %${Math.abs(avgNegGain).toFixed(2)})`;
            let netSign = avgClose > 0 ? '+' : '';
            if (el('stats-tab-net-pct')) el('stats-tab-net-pct').innerText = `${netSign}%${avgClose.toFixed(2)}`;
            let netCard = el('stats-tab-net-card');
            if (netCard) {
                if (avgClose > 0) {
                    netCard.style.background = 'linear-gradient(145deg, rgba(16,185,129,0.05) 0%, rgba(15,23,42,1) 100%)';
                    netCard.style.border = '1px solid rgba(16,185,129,0.2)';
                    if (el('stats-tab-net-pct')) el('stats-tab-net-pct').style.color = 'var(--accent-green)';
                } else if (avgClose < 0) {
                    netCard.style.background = 'linear-gradient(145deg, rgba(239,68,68,0.05) 0%, rgba(15,23,42,1) 100%)';
                    netCard.style.border = '1px solid rgba(239,68,68,0.2)';
                    if (el('stats-tab-net-pct')) el('stats-tab-net-pct').style.color = 'var(--accent-red)';
                } else {
                    netCard.style.background = 'linear-gradient(145deg, rgba(59,130,246,0.05) 0%, rgba(15,23,42,1) 100%)';
                    netCard.style.border = '1px solid rgba(59,130,246,0.2)';
                    if (el('stats-tab-net-pct')) el('stats-tab-net-pct').style.color = 'var(--text-muted)';
                }
            }
            if (el('stats-tab-elite-pos-count')) el('stats-tab-elite-pos-count').innerText = `${elitesPos.length} Adet`;
            if (el('stats-tab-elite-pos-avg')) el('stats-tab-elite-pos-avg').innerText = `(Ort. +%${avgElitePos.toFixed(2)})`;
            if (el('stats-tab-elite-neg-count')) el('stats-tab-elite-neg-count').innerText = `${elitesNeg.length} Adet`;
            if (el('stats-tab-elite-neg-avg')) el('stats-tab-elite-neg-avg').innerText = `(Ort. %${Math.abs(avgEliteNeg).toFixed(2)})`;
            let eliteSign = eliteNet > 0 ? '+' : '';
            if (el('stats-tab-elite-net-pct')) el('stats-tab-elite-net-pct').innerText = `${eliteSign}%${eliteNet.toFixed(2)}`;
            let eliteCard = el('stats-tab-elite-net-card');
            if (eliteCard) {
                if (eliteNet > 0) {
                    eliteCard.style.background = 'linear-gradient(145deg, rgba(234,179,8,0.05) 0%, rgba(15,23,42,1) 100%)';
                    eliteCard.style.border = '1px solid rgba(234,179,8,0.5)';
                    if (el('stats-tab-elite-net-pct')) el('stats-tab-elite-net-pct').style.color = 'var(--accent-yellow)';
                } else {
                    eliteCard.style.background = 'linear-gradient(145deg, rgba(239,68,68,0.05) 0%, rgba(15,23,42,1) 100%)';
                    eliteCard.style.border = '1px solid rgba(239,68,68,0.5)';
                    if (el('stats-tab-elite-net-pct')) el('stats-tab-elite-net-pct').style.color = 'var(--accent-red)';
                }
            }
        }
    }
}

async function fetchStatsTabData() {
    const dailyTbody = document.getElementById('stats-history-tbody');

    if (dailyTbody) {
        dailyTbody.innerHTML = `<tr><td colspan="6" class="text-muted text-center" style="padding:2rem;"><i class="fa-solid fa-spinner fa-spin"></i> Performans arşivi yükleniyor...</td></tr>`;
    }

    try {
        const res = await fetch(`/api/tavan_history?t=` + Date.now());
        const data = await res.json();
        global_stats_data = data;

        if (data.status === 'success' || data.summary) {
            renderStatsMode();
            const history = data.daily_breakdown || data.history || [];
            populateStatsWeekSelect(history);
            renderStatsHistoryTable(history);
        } else {
            if (dailyTbody) dailyTbody.innerHTML = `<tr><td colspan="6" class="text-red text-center" style="padding:2rem;">Veri alınamadı: ${data.message || 'Bilinmeyen hata'}</td></tr>`;
        }
    } catch (e) {
        if (dailyTbody) dailyTbody.innerHTML = `<tr><td colspan="6" class="text-red text-center" style="padding:2rem;">Baglanti hatasi: ${e.message}</td></tr>`;
    }
}

function populateStatsWeekSelect(history) {
    const select = document.getElementById('stats-tab-week-select');
    if (!select || select.dataset.populated === '1') return;
    const dates = history.map(h => h.date).filter(Boolean).sort().reverse();
    if (dates.length === 0) return;
    const weeks = new Set();
    dates.forEach(dStr => {
        const d = new Date(dStr + 'T12:00:00');
        // ISO hafta numarasi
        const target = new Date(d.valueOf());
        const dayNr = (d.getDay() + 6) % 7;
        target.setDate(target.getDate() - dayNr + 3);
        const firstThursday = new Date(target.getFullYear(), 0, 4);
        const fDayNr = (firstThursday.getDay() + 6) % 7;
        const week1 = new Date(firstThursday.getFullYear(), 0, 4 + (7 - fDayNr));
        const weekNum = 1 + Math.round((target - week1) / (7 * 24 * 3600 * 1000));
        weeks.add(`${target.getFullYear()}-W${String(weekNum).padStart(2, '0')}`);
    });
    const sortedWeeks = Array.from(weeks).sort().reverse();
    sortedWeeks.forEach(w => {
        const opt = document.createElement('option');
        opt.value = w;
        opt.textContent = w + ' Haftası';
        select.appendChild(opt);
    });
    select.dataset.populated = '1';
}

function applyStatsWeekFilter() {
    const weekVal = document.getElementById('stats-tab-week-select')?.value || '';
    const history = (global_stats_data && (global_stats_data.daily_breakdown || global_stats_data.history)) || [];
    if (!weekVal) {
        renderStatsHistoryTable(history);
        return;
    }
    const [year, weekStr] = weekVal.split('-W');
    const simple = new Date(year, 0, 1 + (weekStr - 1) * 7);
    const dow = simple.getDay();
    const ISOweekStart = new Date(simple);
    if (dow <= 4)
        ISOweekStart.setDate(simple.getDate() - simple.getDay() + 1);
    else
        ISOweekStart.setDate(simple.getDate() + 8 - simple.getDay());
    const startISO = ISOweekStart.toISOString().slice(0, 10);
    const endD = new Date(ISOweekStart);
    endD.setDate(endD.getDate() + 4);
    const endISO = endD.toISOString().slice(0, 10);
    renderStatsHistoryTable(history.filter(h => h.date >= startISO && h.date <= endISO));
}

function renderStatsHistoryTable(history) {
    const dailyTbody = document.getElementById('stats-history-tbody');
    if (!dailyTbody) return;
    dailyTbody.innerHTML = '';
    if (history.length === 0) {
        dailyTbody.innerHTML = `<tr><td colspan="6" class="text-muted text-center" style="padding:2rem;">Henüz kaydedilmiş seans bulunmuyor.</td></tr>`;
        return;
    }
    history.forEach(h => {
        const tr = document.createElement('tr');
        const avgMax = h.avg_max_gain_pct || 0;
        const avgClose = h.avg_closing_gain_pct || 0;
        const closeColor = avgClose >= 0 ? 'var(--accent-green)' : 'var(--accent-red)';
        const closeSign = avgClose >= 0 ? '+' : '';
        tr.style.cursor = 'pointer';
        tr.onclick = () => openStatsDetailModal('daily_all', h.date);
        tr.title = `${h.date} Tarihli Hisseleri Görmek İçin Tıklayın`;
        tr.innerHTML = `
            <td><i class="fa-regular fa-calendar" style="color:var(--text-muted);"></i> ${h.date}</td>
            <td style="color:var(--accent-blue); font-weight:bold;">${h.total_candidates || h.total_signals || 0}</td>
            <td style="color:var(--accent-green); font-weight:bold;">${h.hit_ceiling_count || h.hit_ceiling || 0} Tavan (%${h.hit_ceiling_pct || h.tavan_rate || 0})</td>
            <td style="color:var(--accent-blue); font-weight:bold;">${h.hit_plus5_count || h.hit_plus5 || 0} Adet (%${h.hit_plus5_pct || h.plus5_rate || 0})</td>
            <td style="color:var(--accent-yellow); font-weight:bold;">+%${avgMax.toFixed(2)}</td>
            <td style="color:${closeColor}; font-weight:bold;">${closeSign}%${avgClose.toFixed(2)}</td>
        `;
        dailyTbody.appendChild(tr);
    });
}

// ============================================================
// 📊 ISTATISTIK DETAY MODALI FONKSIYONLARI
// ============================================================
function openStatsDetailModal(type, date = null) {
    if (!global_stats_data) return;
    const modal = document.getElementById('stats-detail-modal');
    const title = document.getElementById('stats-detail-title');
    const content = document.getElementById('stats-detail-content');
    if (!modal || !title || !content) return;
    
    let items = [];
    let titleText = '';
    
    let allItems = [];
    let isDaily = (typeof current_stats_mode !== 'undefined' && current_stats_mode === 'daily');
    let prefix = isDaily ? 'Günün' : 'Tüm Zamanların';

    if (isDaily) {
        const history = global_stats_data.daily_breakdown || global_stats_data.history || [];
        if (history.length > 0) {
            allItems = history[0].all_symbols || [];
        }
    } else {
        allItems = global_stats_data.summary?.all_time_symbols || [];
    }
    
    if (type === 'tavan') {
        items = allItems.filter(it => it.hit_ceiling);
        titleText = `<i class="fa-solid fa-rocket"></i> ${prefix} Tavan Hisseleri`;
    } else if (type === 'plus5') {
        items = allItems.filter(it => it.hit_plus5);
        titleText = `<i class="fa-solid fa-chart-line"></i> ${prefix} +%5 Yapan Hisseleri`;
    } else if (type === 'positive_close') {
        items = allItems.filter(it => (it.closing_gain_pct || 0) > 0);
        titleText = `<i class="fa-solid fa-arrow-trend-up"></i> ${isDaily ? 'Günü' : 'Tüm Zamanlarda'} Kârda Kapatanlar`;
    } else if (type === 'negative_close') {
        items = allItems.filter(it => (it.closing_gain_pct || 0) < 0);
        titleText = `<i class="fa-solid fa-arrow-trend-down"></i> ${isDaily ? 'Günü' : 'Tüm Zamanlarda'} Zararda Kapatanlar`;
    } else if (type === 'elite_positive_close') {
        items = allItems.filter(it => (it.closing_gain_pct || 0) > 0 && (it.morning_score >= 99.9));
        titleText = `<i class="fa-solid fa-medal text-yellow"></i> ${isDaily ? 'Günün' : 'Tüm Zamanların'} Elit Kârda Kapatanları (100 Puan)`;
    } else if (type === 'elite_negative_close') {
        items = allItems.filter(it => (it.closing_gain_pct || 0) < 0 && (it.morning_score >= 99.9));
        titleText = `<i class="fa-solid fa-medal text-yellow"></i> ${isDaily ? 'Günün' : 'Tüm Zamanların'} Elit Zararda Kapatanları (100 Puan)`;
    } else if (type === 'elite_all') {
        items = allItems.filter(it => it.morning_score >= 99.9);
        titleText = `<i class="fa-solid fa-medal text-yellow"></i> ${isDaily ? 'Günün' : 'Tüm Zamanların'} Tüm Elit Önerileri (100 Puan)`;
    } else if (type === 'all') {
        items = allItems;
        titleText = `<i class="fa-solid fa-list-ul"></i> ${isDaily ? 'Günün' : 'Tüm Zamanların'} Tüm Önerileri`;
    } else if (type === 'daily_all' && date) {
        const dayData = (global_stats_data.daily_breakdown || []).find(d => d.date === date);
        items = dayData?.all_symbols || [];
        titleText = `<i class="fa-regular fa-calendar"></i> ${date} Tarihli Tüm Öneriler`;
    }
    
    
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
    
    if (items.length === 0) {
        content.innerHTML = '<div style="color:var(--text-muted); padding:1rem;">Kayıt bulunamadı.</div>';
    } else {
        items.forEach(item => {
            const sym = item.symbol || item;
            const dt = item.date ? `<div style="font-size:0.75rem; color:var(--text-muted); font-weight:600; margin-bottom:4px;">${item.date} <span style="color:var(--accent-blue);">${item.snapshot_time || '10:15'}</span></div>` : '';
            
            const mPrice = item.morning_price ? item.morning_price.toFixed(2) : '-';
            const mPct = item.morning_gain_pct !== undefined ? item.morning_gain_pct.toFixed(2) : '-';
            const mColor = item.morning_gain_pct > 0 ? 'var(--accent-green)' : (item.morning_gain_pct < 0 ? 'var(--accent-red)' : 'var(--text-muted)');
            
            // Calculate True Daily Closing Percentage
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
            const cColor = trueCPct > 0 ? 'var(--accent-green)' : (trueCPct < 0 ? 'var(--accent-red)' : 'var(--text-muted)');
            
            const maxG = item.max_gain_pct !== undefined ? item.max_gain_pct.toFixed(2) : (item.max_gain !== undefined ? item.max_gain : '-');

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
            
            
            // Get today's date in YYYY-MM-DD
            const todayObj = new Date();
            const yyyy = todayObj.getFullYear();
            const mm = String(todayObj.getMonth() + 1).padStart(2, '0');
            const dd = String(todayObj.getDate()).padStart(2, '0');
            const todayStr = `${yyyy}-${mm}-${dd}`;
            
            const closeLabel = (item.date === todayStr) ? 'Anlık:' : 'Kapanış:';
            
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
                    <span style="color:var(--text-muted);">${closeLabel}</span>
                    <span><b style="color:#fff;">${cPrice}</b> (<span style="color:${cColor}">${cPct > 0 ? '+' : ''}${cPct}%</span>)</span>
                </div>
                <div style="display:flex; justify-content:space-between; font-size:0.75rem; margin-bottom:8px; background:rgba(0,0,0,0.2); padding:4px; border-radius:4px;">
                    <span style="color:var(--text-muted);">Net Getiri:</span>
                    <span style="color:${diffColor}; font-weight:bold;">${diffStr} ₺ (${diffPctStr}%)</span>
                </div>
                <div>${hitStatus}</div>
            `;
            content.appendChild(card);
        });
    }
    
    modal.style.display = 'block';
    document.body.style.overflow = 'hidden';
}

// ============================================================
// 🔧 ORTAK RENDER YARDIMCILARI (Hem Modal hem Sekme İçin)
// ============================================================

function renderHistoryKpis(summ, prefix) {
    if (!summ) return;
    const el = (id) => document.getElementById(prefix + id);
    const maxP = summ.cumulative_avg_max_gain_pct || 0;
    const clsP = summ.cumulative_avg_closing_gain_pct || 0;
    const wrnP = summ.ahlatci_warrant_avg_gain_pct || 0;

    if (el('total-days')) el('total-days').innerText = `${summ.total_days_tracked || 0} Seans`;
    if (el('total-candidates-sub')) el('total-candidates-sub').innerText = `Toplam ${summ.total_candidates_tracked || 0} Oneri`;
    if (el('tavan-rate')) el('tavan-rate').innerText = `%${summ.tavan_success_pct || 0}`;
    if (el('tavan-cnt-sub')) el('tavan-cnt-sub').innerText = `${summ.total_hit_ceiling || 0} / ${summ.total_candidates_tracked || 0} Tavan`;
    if (el('plus5-rate')) el('plus5-rate').innerText = `%${summ.plus5_success_pct || 0}`;
    if (el('plus5-cnt-sub')) el('plus5-cnt-sub').innerText = `${summ.total_hit_plus5 || 0} / ${summ.total_candidates_tracked || 0} Kazandirdi`;
    if (el('avg-max-gain')) el('avg-max-gain').innerText = `${maxP > 0 ? '+' : ''}%${maxP.toFixed(2)}`;
    if (el('avg-close-sub')) el('avg-close-sub').innerText = `Kapanis Ort: ${clsP > 0 ? '+' : ''}%${clsP.toFixed(2)}`;
    if (el('warrant-avg-gain')) el('warrant-avg-gain').innerText = `${wrnP > 0 ? '+' : ''}%${wrnP.toFixed(2)}`;
}

function renderHourlyCards(hourlyList, container) {
    if (!container) return;
    if (!hourlyList || hourlyList.length === 0) {
        container.innerHTML = `<div style="color:var(--text-muted); font-size:0.85rem; padding:1rem;">Saatlik veri bulunamadi.</div>`;
        return;
    }

    // Saatlere göre sırala
    const sortOrder = { '10:15': 1, '11:30': 2, '14:00': 3, '16:00': 4 };
    hourlyList.sort((a, b) => (sortOrder[a.time] || 9) - (sortOrder[b.time] || 9));

    const colorMap = {
        '10:15': { bg: 'rgba(251, 146, 60, 0.1)', border: 'rgba(251, 146, 60, 0.4)', text: '#fb923c', icon: 'fa-sun' },
        '11:30': { bg: 'rgba(250, 204, 21, 0.1)', border: 'rgba(250, 204, 21, 0.35)', text: '#facc15', icon: 'fa-cloud-sun' },
        '14:00': { bg: 'rgba(56, 189, 248, 0.1)', border: 'rgba(56, 189, 248, 0.35)', text: '#38bdf8', icon: 'fa-circle-half-stroke' },
        '16:00': { bg: 'rgba(168, 85, 247, 0.1)', border: 'rgba(168, 85, 247, 0.35)', text: '#c084fc', icon: 'fa-moon' },
    };

    container.innerHTML = hourlyList.map(h => {
        const c = colorMap[h.time] || { bg: 'rgba(255,255,255,0.04)', border: 'rgba(255,255,255,0.15)', text: '#94a3b8', icon: 'fa-clock' };
        const tavanColor = h.tavan_pct >= 75 ? '#10b981' : (h.tavan_pct >= 50 ? '#facc15' : '#ef4444');
        const plus5Color = h.plus5_pct >= 80 ? '#38bdf8' : (h.plus5_pct >= 60 ? '#10b981' : '#facc15');
        const bestTime = hourlyList.reduce((a, b) => (a.tavan_pct > b.tavan_pct ? a : b), hourlyList[0]);
        const isBest = h.time === bestTime.time;

        return `
            <div style="background:${c.bg}; border:1px solid ${c.border}; border-radius:10px; padding:1rem; position:relative; ${isBest ? 'box-shadow: 0 0 18px ' + c.border + ';' : ''}">
                ${isBest ? `<div style="position:absolute; top:-10px; right:10px; background:${c.text}; color:#000; font-size:0.65rem; font-weight:800; padding:2px 8px; border-radius:4px;">EN BASARILI</div>` : ''}
                <div style="font-size:1.1rem; font-weight:800; color:${c.text}; display:flex; align-items:center; gap:8px; margin-bottom:0.7rem;">
                    <i class="fa-solid ${c.icon}"></i> ${h.label || h.time}
                </div>
                <div style="display:grid; grid-template-columns:1fr 1fr; gap:0.5rem;">
                    <div style="background:rgba(255,255,255,0.04); border-radius:6px; padding:0.5rem; text-align:center;">
                        <div style="font-size:0.65rem; color:var(--text-muted); text-transform:uppercase; font-weight:600;">Tavan Kilidi</div>
                        <div style="font-size:1.3rem; font-weight:800; color:${tavanColor};">%${h.tavan_pct}</div>
                        <div style="font-size:0.65rem; color:var(--text-muted);">${h.tavan_hits}/${h.candidates} hisse</div>
                    </div>
                    <div style="background:rgba(255,255,255,0.04); border-radius:6px; padding:0.5rem; text-align:center;">
                        <div style="font-size:0.65rem; color:var(--text-muted); text-transform:uppercase; font-weight:600;">+%5 Kar</div>
                        <div style="font-size:1.3rem; font-weight:800; color:${plus5Color};">%${h.plus5_pct}</div>
                        <div style="font-size:0.65rem; color:var(--text-muted);">${h.plus5_hits}/${h.candidates} hisse</div>
                    </div>
                </div>
                <div style="display:flex; justify-content:space-between; margin-top:0.6rem; font-size:0.78rem;">
                    <div style="color:var(--text-muted);">Ort. Zirve: <span style="color:#facc15; font-weight:800;">+%${h.avg_max_gain_pct}</span></div>
                    <div style="color:var(--text-muted);">Varant: <span style="color:#c084fc; font-weight:800;">+%${h.warrant_gain_pct}</span></div>
                </div>
                <div style="margin-top:0.5rem; font-size:0.7rem; color:var(--text-muted); text-align:right;">${h.candidates} oneri tarama yapildi</div>
            </div>`;
    }).join('');
}


function renderHallOfFame(hofList, tbody) {
    if (!tbody) return;
    if (!hofList || hofList.length === 0) {
        tbody.innerHTML = `<tr><td colspan="7" class="text-muted text-center" style="padding:2rem;">Kayit bulunamadi.</td></tr>`;
        return;
    }
    tbody.innerHTML = '';
    hofList.forEach((h, idx) => {
        const tr = document.createElement('tr');
        const rankIcon = idx === 0 ? '🥇' : (idx === 1 ? '🥈' : (idx === 2 ? '🥉' : `#${idx + 1}`));
        tr.innerHTML = `
            <td><div style="font-weight:800; color:#fff; font-size:0.88rem;">${rankIcon}</div></td>
            <td><div style="font-weight:800; color:#fff; font-size:0.88rem;">${h.symbol}</div></td>
            <td style="color:var(--text-muted); font-weight:bold; text-align:center;">${h.appearances} Gun</td>
            <td>
                <span style="color:#10b981; font-weight:800; font-size:0.85rem;">%${h.tavan_success_pct}</span>
                <div style="font-size:0.68rem; color:var(--text-muted);">${h.tavan_hits} Kez Tavan</div>
            </td>
            <td>
                <span style="color:#38bdf8; font-weight:800; font-size:0.85rem;">%${h.plus5_success_pct}</span>
                <div style="font-size:0.68rem; color:var(--text-muted);">${h.plus5_hits} Kez +%5</div>
            </td>
            <td style="color:#facc15; font-weight:800;">+ %${h.avg_max_gain_pct}</td>
            <td><div style="font-weight:800; color:#c084fc; font-size:0.82rem;">${h.ahlatci_warrant || '-'}</div></td>`;
        tbody.appendChild(tr);
    });
}

// ============================================================
// 📱 MOBİL GRAFİK YARDIMCILARI
// ============================================================

// Yatay Döndürme İpucu
let rotateHintDismissed = localStorage.getItem('rotate-hint-dismissed') === 'true';

function showRotateHint() {
    if (rotateHintDismissed || window.innerWidth > 850) return;
    const overlay = document.getElementById('rotateHintOverlay');
    if (overlay && window.matchMedia('(orientation: portrait)').matches) {
        overlay.classList.add('active');
    }
}
function dismissRotateHint() {
    rotateHintDismissed = true;
    localStorage.setItem('rotate-hint-dismissed', 'true');
    const overlay = document.getElementById('rotateHintOverlay');
    if (overlay) overlay.classList.remove('active');
}

// Yataya geçince ipucunu otomatik kapat
window.matchMedia('(orientation: landscape)').addEventListener('change', e => {
    if (e.matches) {
        const overlay = document.getElementById('rotateHintOverlay');
        if (overlay) overlay.classList.remove('active');
    }
});

// Tam Ekran Grafik Modu
function openChartFullscreen(canvasId, title) {
    const originalCanvas = document.getElementById(canvasId);
    if (!originalCanvas) return;

    const overlay = document.getElementById('chartFullscreenOverlay');
    const titleEl = document.getElementById('chart-fs-title');
    const body = document.getElementById('chart-fs-body');
    if (!overlay || !body) return;

    if (titleEl) titleEl.innerHTML = `<i class="fa-solid fa-chart-line"></i> ${title || 'Grafik'}`;

    // Canvas'ı klonla
    body.innerHTML = '';
    const clone = originalCanvas.cloneNode(true);
    clone.style.width = '100%';
    clone.style.height = '100%';
    clone.style.maxHeight = '80vh';
    body.appendChild(clone);

    overlay.classList.add('active');
    document.body.style.overflow = 'hidden';
}

function closeChartFullscreen() {
    const overlay = document.getElementById('chartFullscreenOverlay');
    if (overlay) overlay.classList.remove('active');
    document.body.style.overflow = '';
}

// Dashboard yüklenince grafiklere "Büyüt" butonu ekle
function injectChartExpandButtons() {
    if (window.innerWidth > 850) return;
    document.querySelectorAll('.chart-container').forEach((container, idx) => {
        if (container.querySelector('.chart-expand-btn')) return;
        const canvas = container.querySelector('canvas');
        if (!canvas) return;

        const canvasId = canvas.id || `chart-canvas-${idx}`;
        if (!canvas.id) canvas.id = canvasId;

        const btn = document.createElement('button');
        btn.className = 'chart-expand-btn';
        btn.innerHTML = '<i class="fa-solid fa-expand"></i> Büyüt';
        btn.onclick = function() {
            // İlk açılışta yatay döndürme ipucu göster
            if (!rotateHintDismissed) showRotateHint();
            openChartFullscreen(canvasId, container.closest('.card')?.querySelector('.card-title')?.textContent || 'Grafik');
        };
        container.style.position = 'relative';
        container.appendChild(btn);
    });
}

// Sayfa yüklenince ve analiz tamamlanınca çağır
const _origSwitchMainTab = window.switchMainTab;
if (typeof _origSwitchMainTab === 'function') {
    // Dashboard sekmesine geçince butonları ekle
    const origFn = switchMainTab;
}

// 500ms sonra otomatik inject (sayfa yüklenince)
setTimeout(injectChartExpandButtons, 1500);

// Analiz tamamlanınca tekrar inject et (yeni grafikler oluşabilir)
const _chartObserver = new MutationObserver(() => {
    setTimeout(injectChartExpandButtons, 500);
});
const dashWrapper = document.getElementById('dashboard-wrapper');
if (dashWrapper) {
    _chartObserver.observe(dashWrapper, { childList: true, subtree: true });
}

// ========== SİMÜLASYON MOTORU ==========
let globalSimData = null;

// Simülasyon sayfası otomatik yenileme: kullanıcı inceleyebilmesi için
// durdurulabilir. Durdurulunca yalnızca "Şimdi Yenile" ile tazelenir.
let simAutoRefresh = true;

function toggleSimAutoRefresh() {
    simAutoRefresh = !simAutoRefresh;
    const btn = document.getElementById('sim-auto-refresh-toggle');
    if (btn) {
        btn.innerHTML = simAutoRefresh
            ? '<i class="fa-solid fa-pause"></i> Otomatik Yenileme: AÇIK'
            : '<i class="fa-solid fa-play"></i> Otomatik Yenileme: KAPALI';
        btn.style.borderColor = simAutoRefresh ? 'var(--border-color)' : 'var(--accent-yellow)';
        btn.style.color = simAutoRefresh ? 'var(--text-main)' : 'var(--accent-yellow)';
    }
}

function refreshSimNow() {
    fetchSimulationData();
}

async function fetchSimulationData() {
    const tbody = document.getElementById('sim-trade-log-tbody');
    if (tbody) tbody.innerHTML = '<tr><td colspan="6" class="text-muted text-center" style="padding:2rem;"><i class="fa-solid fa-spinner fa-spin"></i> İşlem Geçmişi Yükleniyor...</td></tr>';

    try {
        const res = await fetch(`/api/simulation/daily_pnl?t=` + Date.now());
        const data = await res.json();

        if (data.status === 'success') {
            globalSimData = data;
            notifyNewTradeEvents(data.trades || []);
            fetchLiveOrders();
            fetchLiveTerminal();
            ltRefreshResetUI();
            fetchAdminResetRequests();
            
            // Calculate KPIs
            const equityCurve = data.equity_curve || [];
            const trades = data.trades || [];
            
            let startBakiye = 0;
            let endBakiye = 0;
            let totalGetiri = 0;
            
            if (equityCurve.length > 0) {
                startBakiye = equityCurve[0].start_equity;
                endBakiye = equityCurve[equityCurve.length - 1].end_equity;
                if (startBakiye > 0) {
                    totalGetiri = ((endBakiye - startBakiye) / startBakiye) * 100;
                }
            }
            
            const isProfit = totalGetiri >= 0;
            const el = (id) => document.getElementById(id);
            if (el('sim-kpi-start')) el('sim-kpi-start').innerText = startBakiye.toLocaleString('tr-TR', {minimumFractionDigits:2}) + ' ₺';
            if (el('sim-kpi-end')) el('sim-kpi-end').innerText = endBakiye.toLocaleString('tr-TR', {minimumFractionDigits:2}) + ' ₺';
            if (el('sim-kpi-total-pct')) {
                el('sim-kpi-total-pct').innerText = (isProfit ? '+' : '') + totalGetiri.toFixed(2) + '%';
                el('sim-kpi-total-pct').style.color = isProfit ? 'var(--accent-green)' : 'var(--accent-red)';
            }
            if (el('sim-kpi-trades')) el('sim-kpi-trades').innerText = trades.length;
            
            // Render Equity Curve Chart
            renderEquityCurveChart(equityCurve);
            
            // Render Trades Table
            if (tbody) {
                tbody.innerHTML = '';
                if (trades.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="8" class="text-muted text-center" style="padding:2rem;">Kayıtlı işlem bulunamadı.</td></tr>';
                } else {
                    trades.forEach(t => {
                        const tr = document.createElement('tr');
                        const isClosed = t.exit_time && t.exit_price;
                        const pnlColor = t.pnl_pct >= 0 ? 'var(--accent-green)' : 'var(--accent-red)';
                        const pnlSign = t.pnl_pct >= 0 ? '+' : '';
                        
                        const exitTimeStr = isClosed ? t.exit_time : '<span style="color:var(--accent-yellow)">İşlemde</span>';
                        const exitPriceStr = isClosed ? `₺${t.exit_price.toFixed(2)}` : '<span style="color:var(--text-muted)">-</span>';
                        // Acik pozisyonlarda da anlik K/Z goster (sim motoru hesaplar)
                        const pnlValStr = `${pnlSign}₺${(t.pnl_val || 0).toFixed(2)}`;
                        const pnlPctStr = `${pnlSign}${(t.pnl_pct || 0).toFixed(2)}%`;
                        const strategyStr = t.strategy_name
                            ? `<div style="margin-top:0.25rem; color:var(--accent-blue); font-size:0.7rem;" title="${t.entry_checks || ''}">${t.strategy_name}${t.risk_amount ? ` · Risk: ₺${Number(t.risk_amount).toFixed(0)}` : ''}</div>`
                            : '';
                        const statusStr = (isClosed ? (t.exit_reason || 'Kapandı') : '<span style="color:var(--accent-yellow); font-weight:bold;"><i class="fa-solid fa-spinner fa-spin"></i> AÇIK POZİSYON</span>') + strategyStr;

                        const formatDt = (iso) => {
                            if (!iso) return '-';
                            try {
                                const d = new Date(iso);
                                if(isNaN(d.getTime())) return iso;
                                const pad = n => n.toString().padStart(2, '0');
                                return pad(d.getDate()) + '/' + pad(d.getMonth()+1) + ' ' + pad(d.getHours()) + ':' + pad(d.getMinutes());
                            } catch(e) { return iso; }
                        };
                        const entryTimeFmt = formatDt(t.entry_time);
                        const exitTimeFmt = isClosed ? formatDt(t.exit_time) : '<span style="color:var(--accent-yellow)">İşlemde</span>';

                        tr.innerHTML = `
                            <td>${entryTimeFmt}</td>
                            <td>${exitTimeFmt}</td>
                            <td style="font-weight:bold; color:var(--text-light);">${t.symbol}</td>
                            <td>${t.shares || '-'}</td>
                            <td>₺${t.entry_price.toFixed(2)}</td>
                            <td>${exitPriceStr}</td>
                            <td style="color:${pnlColor}; font-weight:bold;">${pnlValStr}</td>
                            <td style="color:${pnlColor}; font-weight:bold;">${pnlPctStr}</td>
                            <td>${statusStr}</td>
                        `;
                        tbody.appendChild(tr);
                    });
                }
            }
        } else {
            if (tbody) tbody.innerHTML = '<tr><td colspan="6" class="text-red text-center" style="padding:2rem;">Simülasyon verisi alınamadı.</td></tr>';
        }
    } catch (e) {
        if (tbody) tbody.innerHTML = '<tr><td colspan="6" class="text-red text-center" style="padding:2rem;">Bağlantı hatası: ' + e.message + '</td></tr>';
    }
}

function renderSimulationPerformance(performance, targetId = 'sim-performance-summary') {
    const container = document.getElementById(targetId);
    if (!container) return;
    const total = Number(performance.total_trades || 0);
    if (!total) {
        container.style.display = 'block';
        container.innerHTML = '<span style="color:var(--text-muted); font-size:.85rem;">Strateji performansı, kapatılmış ilk işlemlerden sonra burada oluşur.</span>';
        return;
    }
    const metric = (label, value, color) => `<div style="min-width:120px;"><div style="font-size:.7rem; color:var(--text-muted); text-transform:uppercase;">${label}</div><strong style="font-size:1rem; color:${color};">${value}</strong></div>`;
    const pf = performance.profit_factor === null || performance.profit_factor === undefined ? '—' : performance.profit_factor.toFixed(2);
    const rows = (performance.strategies || []).map(item => {
        const state = item.ready ? 'Ölçümlü' : `Yetersiz örnek (${item.trades}/${performance.minimum_samples})`;
        const color = item.net_pnl >= 0 ? 'var(--accent-green)' : 'var(--accent-red)';
        const itemPf = item.profit_factor === null || item.profit_factor === undefined ? '—' : item.profit_factor.toFixed(2);
        return `<div style="display:grid; grid-template-columns:minmax(150px,2fr) repeat(4,minmax(76px,1fr)); gap:.55rem; padding:.65rem 0; border-top:1px solid var(--border-color); font-size:.82rem; align-items:center;"><strong>${item.strategy_name}</strong><span>${item.trades} işlem</span><span>%${item.win_rate.toFixed(1)} başarı</span><span>PF ${itemPf}</span><span style="color:${color}; font-weight:700;">${item.net_pnl >= 0 ? '+' : ''}₺${item.net_pnl.toFixed(2)} · ${state}</span></div>`;
    }).join('');
    container.style.display = 'block';
    container.innerHTML = `<div style="display:flex; gap:1.25rem; justify-content:space-between; flex-wrap:wrap; margin-bottom:.8rem;"><h3 class="card-title" style="margin:0; font-size:1rem;"><i class="fa-solid fa-chart-simple text-green"></i> Strateji Karnesi</h3><div style="display:flex; gap:1.25rem; flex-wrap:wrap;">${metric('Kazanma oranı', '%' + Number(performance.win_rate || 0).toFixed(1), 'var(--accent-green)')}${metric('Net PnL', (performance.net_pnl >= 0 ? '+' : '') + '₺' + Number(performance.net_pnl || 0).toFixed(2), performance.net_pnl >= 0 ? 'var(--accent-green)' : 'var(--accent-red)')}${metric('Profit factor', pf, 'var(--accent-blue)')}${metric('Maks. düşüş', '₺' + Number(performance.max_drawdown_tl || 0).toFixed(2), 'var(--accent-yellow)')}</div></div>${rows}`;
}

let _knownTradeEvents = new Set();
let _tradeAudioContext = null;
let _tradeNotifyReady = false;

function enableTradeNotifications() {
    _tradeNotifyReady = true;
    try {
        _tradeAudioContext = _tradeAudioContext || new (window.AudioContext || window.webkitAudioContext)();
        if (_tradeAudioContext.state === 'suspended') _tradeAudioContext.resume();
    } catch (_) {}
    if ('Notification' in window && Notification.permission === 'default') {
        Notification.requestPermission().catch(() => {});
    }
    const status = document.getElementById('sim-notify-status');
    if (status) status.textContent = 'Bildirim ve ses aktif';
}

function playTradeAlert(kind) {
    if (!_tradeNotifyReady) return;
    try {
        const ctx = _tradeAudioContext || new (window.AudioContext || window.webkitAudioContext)();
        _tradeAudioContext = ctx;
        const now = ctx.currentTime;
        const oscillator = ctx.createOscillator();
        const gain = ctx.createGain();
        oscillator.type = kind === 'BUY' ? 'sine' : 'square';
        oscillator.frequency.setValueAtTime(kind === 'BUY' ? 880 : 440, now);
        oscillator.frequency.exponentialRampToValueAtTime(kind === 'BUY' ? 1320 : 220, now + 0.18);
        gain.gain.setValueAtTime(0.0001, now);
        gain.gain.exponentialRampToValueAtTime(0.18, now + 0.02);
        gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.22);
        oscillator.connect(gain).connect(ctx.destination);
        oscillator.start(now);
        oscillator.stop(now + 0.24);
    } catch (_) {}
}

function notifyNewTradeEvents(trades) {
    const events = [];
    trades.forEach(t => {
        const entryKey = `BUY:${t.id || `${t.symbol}:${t.entry_time}`}`;
        if (!_knownTradeEvents.has(entryKey)) {
            _knownTradeEvents.add(entryKey);
            if (t.entry_time) events.push({kind: 'BUY', symbol: t.symbol, price: t.entry_price, time: t.entry_time});
        }
        if (t.exit_time) {
            const exitKey = `SELL:${t.id || `${t.symbol}:${t.exit_time}`}`;
            if (!_knownTradeEvents.has(exitKey)) {
                _knownTradeEvents.add(exitKey);
                events.push({kind: 'SELL', symbol: t.symbol, price: t.exit_price, time: t.exit_time, reason: t.exit_reason});
            }
        }
    });
    if (!events.length) return;
    events.slice(-4).forEach(event => {
        playTradeAlert(event.kind);
        if ('Notification' in window && Notification.permission === 'granted') {
            new Notification(event.kind === 'BUY' ? 'VARANTRADAR — ALIŞ' : 'VARANTRADAR — SATIŞ', {
                body: `${event.symbol} · ₺${Number(event.price || 0).toFixed(2)}${event.reason ? ` · ${event.reason}` : ''}`,
                tag: `trade-${event.kind}-${event.symbol}`
            });
        }
    });
    const status = document.getElementById('sim-notify-status');
    if (status) status.textContent = `${events.length} yeni işlem bildirimi`;
}

let equityChartInstance = null;

// ========== ANLIK İŞLEM TERMİNALİ ==========
let ltTimerStarted = false;

async function fetchLiveTerminal() {
    try {
        const res = await fetch('/api/simulation/terminal?t=' + Date.now());
        const data = await res.json();
        if (data.status !== 'success') return;
        const t = data.terminal || {};
        if (t.owner) window.__vrOwnerKey = t.owner;

        const el = (id) => document.getElementById(id);
        const fmt = (v) => (v || 0).toLocaleString('tr-TR', {minimumFractionDigits: 2, maximumFractionDigits: 2}) + ' ₺';

        if (el('lt-cash')) el('lt-cash').innerText = fmt(t.cash);
        if (el('lt-invested')) el('lt-invested').innerText = fmt(t.invested);
        if (el('lt-open-pnl')) {
            const pnl = t.open_pnl || 0;
            el('lt-open-pnl').innerText = (pnl >= 0 ? '+' : '') + fmt(pnl);
            el('lt-open-pnl').style.color = pnl >= 0 ? 'var(--accent-green)' : 'var(--accent-red)';
        }
        if (el('lt-equity')) el('lt-equity').innerText = fmt(t.equity);

        // Açık pozisyonlar
        const tbody = el('lt-open-tbody');
        if (tbody) {
            tbody.innerHTML = '';
            const open = t.open || [];
            if (open.length === 0) {
                tbody.innerHTML = '<tr><td colspan="10" style="text-align:center; color:var(--text-muted); padding:1rem;">Açık pozisyon yok. Yukarıdan sembol girip AL tuşuyla pozisyon açabilirsiniz.</td></tr>';
            } else {
                open.forEach(p => {
                    const tr = document.createElement('tr');
                    const entry = p.entry_price || 0;
                    const last = p.last_price || entry;
                    const pct = entry > 0 ? ((last - entry) / entry) * 100 : 0;
                    const pnlVal = (last - entry) * (p.shares || 0);
                    const color = pct >= 0 ? 'var(--accent-green)' : 'var(--accent-red)';
                    const protectedTxt = p.trailing_active
                        ? '<span style="color:var(--accent-green); font-weight:bold;">🔒 ' + (p.stop_price || 0).toFixed(2) + '</span>'
                        : '<span style="color:var(--text-muted);">-</span>';

                    tr.innerHTML = `
                        <td style="font-weight:bold; color:var(--text-light);">${p.symbol}</td>
                        <td>${(p.entry_time || '').slice(11, 16)}</td>
                        <td>${p.shares}</td>
                        <td>₺${entry.toFixed(2)}</td>
                        <td style="color:var(--accent-blue); font-weight:bold;">₺${last.toFixed(2)}</td>
                        <td style="color:${color}; font-weight:bold;">${pnlVal >= 0 ? '+' : ''}₺${pnlVal.toFixed(2)} (${pct >= 0 ? '+' : ''}${pct.toFixed(2)}%)</td>
                        <td style="color:var(--accent-green);">₺${(p.tp_price || 0).toFixed(2)}</td>
                        <td style="color:var(--accent-red);">₺${(p.stop_price || 0).toFixed(2)}</td>
                        <td>${protectedTxt}</td>
                        <td style="white-space:nowrap;">
                            <button onclick="ltEditOrders(${p.id}, ${p.tp_price || 0}, ${p.stop_price || 0}, ${last})" title="Emir Düzenle (TP/SL)" style="background:rgba(59,130,246,0.15); border:1px solid var(--accent-blue); color:var(--accent-blue); border-radius:6px; padding:4px 8px; cursor:pointer; font-size:0.78rem; font-weight:bold; margin-right:4px;">✎</button>
                            <button onclick="ltClosePosition(${p.id})" style="background:rgba(225,29,72,0.15); border:1px solid var(--accent-red); color:var(--accent-red); border-radius:6px; padding:4px 10px; cursor:pointer; font-size:0.78rem; font-weight:bold;">SAT</button>
                        </td>
                    `;
                    tbody.appendChild(tr);
                });
            }
        }

        // Son kapananlar
        const closedTbody = el('lt-closed-tbody');
        if (closedTbody) {
            closedTbody.innerHTML = '';
            const closed = t.closed || [];
            if (closed.length === 0) {
                closedTbody.innerHTML = '<tr><td colspan="6" style="text-align:center; color:var(--text-muted);">Kayıt yok.</td></tr>';
            } else {
                closed.forEach(p => {
                    const tr = document.createElement('tr');
                    const color = (p.pnl_val || 0) >= 0 ? 'var(--accent-green)' : 'var(--accent-red)';
                    const sign = (p.pnl_val || 0) >= 0 ? '+' : '';
                    tr.innerHTML = `
                        <td>${(p.exit_time || '').slice(5, 16)}</td>
                        <td style="font-weight:bold;">${p.symbol}</td>
                        <td>₺${(p.entry_price || 0).toFixed(2)}</td>
                        <td>₺${(p.exit_price || 0).toFixed(2)}</td>
                        <td style="color:${color}; font-weight:bold;">${sign}₺${(p.pnl_val || 0).toFixed(2)} (${sign}${(p.pnl_pct || 0).toFixed(2)}%)</td>
                        <td style="font-size:0.75rem; color:var(--text-muted);">${p.exit_reason || '-'}</td>
                    `;
                    closedTbody.appendChild(tr);
                });
            }
        }

        if (el('lt-last-scan')) {
            const lastUpd = (t.open && t.open.length > 0) ? t.open[0].last_update : null;
            el('lt-last-scan').innerText = lastUpd ? ('Son fiyat: ' + lastUpd.slice(11, 19)) : 'Beklemede';
        }
    } catch (e) {
        console.error('[LiveTerminal]', e);
    }
}

// KAR AL / ZARAR KES: yuzde <-> fiyat senkronu (anlik fiyata gore)
function _ltQuotePrice() {
    const q = document.getElementById('lq-price');
    if (!q) return null;
    const v = parseFloat((q.textContent || '').replace(/[^\d.,]/g, '').replace(',', '.'));
    return (v && v > 0) ? v : null;
}

function ltSyncFromPct(kind) {
    const el = (id) => document.getElementById(id);
    const base = _ltQuotePrice();
    const pctEl = el(kind === 'tp' ? 'lt-tp' : 'lt-sl');
    const priceEl = el(kind === 'tp' ? 'lt-tp-price' : 'lt-sl-price');
    if (!pctEl || !priceEl) return;
    const pct = parseFloat(pctEl.value);
    if (isNaN(pct) || pct <= 0) return;
    if (!base) return; // anlik fiyat yoksa fiyati dokme
    const price = kind === 'tp' ? base * (1 + pct / 100) : base * (1 - pct / 100);
    if (document.activeElement !== priceEl) priceEl.value = price.toFixed(2);
}

function ltSyncFromPrice(kind) {
    const el = (id) => document.getElementById(id);
    const base = _ltQuotePrice();
    const pctEl = el(kind === 'tp' ? 'lt-tp' : 'lt-sl');
    const priceEl = el(kind === 'tp' ? 'lt-tp-price' : 'lt-sl-price');
    if (!pctEl || !priceEl) return;
    const price = parseFloat(priceEl.value);
    if (isNaN(price) || price <= 0 || !base) return;
    const pct = kind === 'tp' ? (price / base - 1) * 100 : (1 - price / base) * 100;
    if (pct <= 0) return; // mantiksiz yon
    if (document.activeElement !== pctEl) pctEl.value = Math.max(0.5, Math.round(pct * 10) / 10);
}

async function ltOpenPosition() {
    const el = (id) => document.getElementById(id);
    const msgEl = el('lt-msg');
    const symbol = (el('lt-symbol')?.value || '').trim().toUpperCase();
    if (!symbol) {
        if (msgEl) { msgEl.innerText = 'Sembol girin'; msgEl.style.color = 'var(--accent-red)'; }
        return;
    }
    const btn = el('lt-buy-btn');
    if (btn) { btn.disabled = true; btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Gönderiliyor'; }

    const tpPriceRaw = parseFloat(el('lt-tp-price')?.value);
    const slPriceRaw = parseFloat(el('lt-sl-price')?.value);

    try {
        const res = await fetch('/api/simulation/terminal/open', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                symbol: symbol,
                allocation: parseFloat(el('lt-allocation')?.value) || 2000,
                tp_pct: parseFloat(el('lt-tp')?.value) || 5,
                sl_pct: parseFloat(el('lt-sl')?.value) || 3,
                tp_price: (!isNaN(tpPriceRaw) && tpPriceRaw > 0) ? tpPriceRaw : null,
                sl_price: (!isNaN(slPriceRaw) && slPriceRaw > 0) ? slPriceRaw : null,
                trailing: el('lt-trailing')?.checked !== false
            })
        });
        const data = await res.json();
        if (msgEl) {
            msgEl.innerText = data.message || (data.status === 'success' ? 'Tamam' : 'Hata');
            msgEl.style.color = data.status === 'success' ? 'var(--accent-green)' : 'var(--accent-red)';
        }
        if (data.status === 'success') {
            if (el('lt-symbol')) el('lt-symbol').value = '';
            if (el('lt-tp-price')) el('lt-tp-price').value = '';
            if (el('lt-sl-price')) el('lt-sl-price').value = '';
        }
        fetchLiveTerminal();
    } catch (e) {
        if (msgEl) { msgEl.innerText = 'Bağlantı hatası'; msgEl.style.color = 'var(--accent-red)'; }
    } finally {
        if (btn) { btn.disabled = false; btn.innerHTML = '<i class="fa-solid fa-cart-plus"></i> AL'; }
        setTimeout(() => { if (msgEl) msgEl.innerText = ''; }, 8000);
    }
}

async function ltEditOrders(id, curTp, curSl, lastPrice) {
    const tpInp = prompt(
        'Yeni KÂR AL fiyatı (₺) — anlık: ' + Number(lastPrice).toFixed(2) + ' TL\n' +
        'Boş bırakırsan değişmez. Mevcut: ' + Number(curTp).toFixed(2), '');
    if (tpInp === null) return;
    const slInp = prompt(
        'Yeni ZARAR KES fiyatı (₺) — anlık: ' + Number(lastPrice).toFixed(2) + ' TL\n' +
        'Boş bırakırsan değişmez. Mevcut: ' + Number(curSl).toFixed(2), '');
    if (slInp === null) return;

    const tpV = parseFloat(tpInp);
    const slV = parseFloat(slInp);
    const body = { id: id };
    if (!isNaN(tpV) && tpV > 0) body.tp_price = tpV;
    if (!isNaN(slV) && slV > 0) body.sl_price = slV;
    if (body.tp_price === undefined && body.sl_price === undefined) return;

    try {
        const res = await fetch('/api/simulation/terminal/update', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(body)
        });
        const data = await res.json();
        alert(data.message || (data.status === 'success' ? 'Güncellendi' : 'Hata'));
        fetchLiveTerminal();
    } catch (e) {
        alert('Bağlantı hatası');
    }
}

async function ltClosePosition(id) {
    if (!confirm('Bu pozisyonu güncel fiyattan SATmak istediğinize emin misiniz?')) return;
    try {
        const res = await fetch('/api/simulation/terminal/close', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({id: id})
        });
        const data = await res.json();
        alert(data.message || (data.status === 'success' ? 'Kapatıldı' : 'Hata'));
        fetchLiveTerminal();
    } catch (e) {
        alert('Bağlantı hatası');
    }
}

// Simülasyon veya Portföy sekmesi görünürken 30 sn'de bir canlı güncelle
setInterval(() => {
    const wrapper = document.getElementById('simulation-wrapper');
    const pfWrapper = document.getElementById('portfolio-wrapper');
    const simVisible = wrapper && wrapper.style.display !== 'none';
    const pfVisible = pfWrapper && pfWrapper.style.display !== 'none';
    if (pfVisible || (simVisible && simAutoRefresh)) {
        fetchLiveTerminal();
        ltRefreshResetUI();
        fetchAdminResetRequests();
    }
}, 30000);

setInterval(() => {
    const wrapper = document.getElementById('simulation-wrapper');
    if (wrapper && wrapper.style.display !== 'none' && simAutoRefresh) {
        fetchSimulationData();
    }
}, 10000);

// ========== DİP & KIRILIM RADARI ==========
let dipCategory = 'ALL';
let dipRowsCache = [];
let dipFetching = false;
let dipRetryCount = 0;

function setDipCategory(cat) {
    dipCategory = cat;
    document.querySelectorAll('.dip-filter-btn').forEach(b => {
        const active = b.dataset.cat === cat;
        b.style.border = active ? '1px solid var(--accent-green)' : '1px solid var(--border-color)';
        b.style.background = active ? 'rgba(16,185,129,0.2)' : 'var(--bg-card)';
        b.style.color = active ? 'var(--accent-green)' : 'var(--text-muted)';
        b.style.fontWeight = active ? '700' : '400';
    });
    renderDipBreakout();
}

async function fetchDipBreakout() {
    if (dipFetching) return;
    dipFetching = true;
    try {
        const res = await fetch('/api/dip_breakout?t=' + Date.now());
        const data = await res.json();
        if (data.status === 'ok' || (data.rows && data.rows.length)) {
            dipRetryCount = 0;
            dipRowsCache = data.rows || [];
            renderDipBreakout();
            // S/R kolonlu diger tablolar dip verisi gelmeden render edildiyse
            // "—" kalmis olurlar; veri gelince yeniden ciz.
            if (typeof renderAllDashboardTables === 'function' && globalDashboardData && Object.keys(globalDashboardData).length) {
                try { renderAllDashboardTables(); } catch (e) { /* sessiz */ }
            }
            const tEl = document.getElementById('time-dip-breakout');
            if (tEl && data.built_at) {
                const d = new Date(data.built_at);
                tEl.innerText = '(Güncelleme: ' + d.toLocaleTimeString('tr-TR', {hour: '2-digit', minute: '2-digit'}) + ')';
            }
        } else {
            // Sunucu veriyi henuz insa ediyorsa bir kac kez daha dene
            if (dipRetryCount < 8) {
                dipRetryCount++;
                setTimeout(fetchDipBreakout, 15000);
            }
            const tbody = document.getElementById('tb-dip-breakout');
            if (tbody) tbody.innerHTML = '<tr><td colspan="12" class="text-muted text-center">' + (data.error || 'Veri hazırlanıyor, birkaç dakika içinde hazır olacak.') + '</td></tr>';
        }
    } catch (e) {
        if (dipRetryCount < 8) {
            dipRetryCount++;
            setTimeout(fetchDipBreakout, 15000);
        }
        const tbody = document.getElementById('tb-dip-breakout');
        if (tbody) tbody.innerHTML = '<tr><td colspan="12" class="text-muted text-center">Bağlantı hatası</td></tr>';
    } finally {
        dipFetching = false;
    }
}

function _dipStageBadge(stage) {
    const map = {
        'ONAYLANDI': ['✅ KIRILIM ONAYLANDI', 'var(--accent-green)'],
        'DENEME': ['🟠 KIRILIM DENEMESİ', '#f59e0b'],
        'YAKLAŞIYOR': ['🔵 KIRILIMA YAKLAŞIYOR', '#3b82f6'],
        'UZAK': ['⚪ UZAK', 'var(--text-muted)'],
    };
    const m = map[stage] || map['UZAK'];
    return '<span style="font-size:0.72rem; font-weight:700; color:' + m[1] + ';">' + m[0] + '</span>';
}

function _dipScoreBar(pct) {
    const color = pct >= 75 ? 'var(--accent-green)' : (pct >= 55 ? '#f59e0b' : 'var(--text-muted)');
    return '<div style="min-width:90px;"><div style="font-size:0.75rem; font-weight:700; color:' + color + ';">%' + pct + '</div>' +
        '<div style="height:4px; background:rgba(255,255,255,0.08); border-radius:2px; margin-top:2px;"><div style="width:' + pct + '%; height:4px; background:' + color + '; border-radius:2px;"></div></div></div>';
}

function renderDipBreakout() {
    const tbody = document.getElementById('tb-dip-breakout');
    if (!tbody) return;
    let rows = dipRowsCache;
    if (dipCategory === 'YENI') {
        rows = rows.filter(r => r.category === 'YENI' || r.is_new);
    } else if (dipCategory !== 'ALL') {
        rows = rows.filter(r => r.category === dipCategory);
    }
    if (!rows.length) {
        tbody.innerHTML = '<tr><td colspan="12" class="text-muted text-center">Bu kategoride şu an aday yok.</td></tr>';
        return;
    }
    const catOrder = {'MOMENTUM': 0, 'DIP_KIRILIM': 1, 'ERKEN_DIP': 2, 'YENI': 3, null: 4};
    rows = [...rows].sort((a, b) => ((catOrder[a.category] ?? 4) - (catOrder[b.category] ?? 4)) || (b.opportunity - a.opportunity));
    const catBadge = {
        'ERKEN_DIP': '<span style="font-size:0.68rem; color:var(--accent-green);">🟢 ERKEN DİP</span>',
        'DIP_KIRILIM': '<span style="font-size:0.68rem; color:#f59e0b;">🟡 DİP→KIR</span>',
        'MOMENTUM': '<span style="font-size:0.68rem; color:var(--accent-red);">🔴 MOMENTUM</span>',
        'YENI': '<span style="font-size:0.68rem; color:#22d3ee;">🆕 YENİ HİSSE</span>',
    };
    const trClsMap = { 'YENI': 'dip-cat-yeni', 'MOMENTUM': 'dip-cat-momentum', 'DIP_KIRILIM': 'dip-cat-dipkir', 'ERKEN_DIP': 'dip-cat-erken' };
    tbody.innerHTML = rows.map(r => {
        const isNew = !!r.is_new;
        const fromDipColor = r.from_dip_pct <= 3 ? 'var(--accent-green)' : (r.from_dip_pct <= 8 ? '#f59e0b' : 'var(--text-muted)');
        const distColor = r.dist_to_res_pct < 0 ? 'var(--accent-red)' : (r.dist_to_res_pct <= 2 ? 'var(--accent-green)' : (r.dist_to_res_pct <= 5 ? '#f59e0b' : 'var(--text-muted)'));
        const supDistColor = (r.support_dist_pct ?? 0) <= 5 ? 'var(--accent-green)' : ((r.support_dist_pct ?? 0) <= 10 ? '#f59e0b' : 'var(--text-muted)');
        const trapColor = r.trap_pct >= 60 ? 'var(--accent-red)' : (r.trap_pct >= 40 ? '#f59e0b' : 'var(--accent-green)');
        let actionColor = 'var(--text-muted)';
        if (r.action === 'AL') actionColor = 'var(--accent-green)';
        else if (r.action === 'DİP AVI') actionColor = '#22d3ee';
        else if (r.action === 'İZLE') actionColor = '#f59e0b';
        else if (r.action === 'GEÇ KALMIŞ') actionColor = '#fb923c';
        else if (r.action === 'YENİ LİSTE') actionColor = '#22d3ee';
        else if (r.action.indexOf('BEKLE ⚠') === 0) actionColor = 'var(--accent-red)';
        const thr = r.threshold_tag ? '<div style="font-size:0.68rem; color:var(--accent-green); font-weight:700;">🔥 DİP+KIRILIM EŞİĞİ</div>' : '';
        const chgColor = r.change_pct >= 0 ? 'var(--accent-green)' : 'var(--accent-red)';
        const dipCell = (r.dip_pct === null || r.dip_pct === undefined)
            ? '<span style="font-size:0.75rem; color:var(--text-muted);">—</span>'
            : _dipScoreBar(r.dip_pct);
        const symBadge = (catBadge[r.category] || '') +
            (isNew && r.category !== 'YENI' ? ' <span style="font-size:0.68rem; color:#22d3ee;">🆕</span>' : '') +
            (isNew && r.listed ? '<br><span style="font-size:0.66rem; color:var(--text-muted);">Liste: ' + r.listed + ' (' + (r.age_days ?? '?') + 'g)</span>' : '');
        const resCell = '₺' + r.resistance.toFixed(2) +
            (r.major_resistance ? '<br><span style="font-size:0.66rem; color:var(--text-muted);">Ana: ₺' + r.major_resistance.toFixed(2) + '</span>' : '');
        const trCls = trClsMap[r.category] || '';
        return '<tr class="' + trCls + '">' +
            '<td><b>' + r.symbol + '</b><br>' + symBadge + '</td>' +
            '<td data-label="Fiyat">₺' + r.price.toFixed(2) + ' <span style="font-size:0.72rem; color:' + chgColor + ';">' + (r.change_pct >= 0 ? '+' : '') + r.change_pct.toFixed(2) + '%</span></td>' +
            '<td data-label="Aşama">' + _dipStageBadge(r.stage) + '</td>' +
            '<td data-label="Dip Oluşumu">' + dipCell + '</td>' +
            '<td class="dip-secondary" data-label="Dip">₺' + r.dip_price.toFixed(2) + '</td>' +
            '<td class="dip-secondary" data-label="Dipten" style="color:' + fromDipColor + ';">+' + r.from_dip_pct.toFixed(1) + '%</td>' +
            '<td data-label="Destek">₺' + (r.support ?? r.dip_price).toFixed(2) + ' <span style="font-size:0.7rem; color:' + supDistColor + ';">-' + (r.support_dist_pct ?? 0).toFixed(1) + '%</span></td>' +
            '<td data-label="Direnç">' + resCell + '</td>' +
            '<td data-label="Dirence" style="color:' + distColor + ';">' + r.dist_to_res_pct.toFixed(2) + '%</td>' +
            '<td data-label="Tuzak" style="color:' + trapColor + '; font-weight:700;">%' + r.trap_pct + '</td>' +
            '<td data-label="İşlem"><span style="font-size:0.75rem; font-weight:800; color:' + actionColor + ';">' + r.action + '</span>' + thr + '</td>' +
            '<td data-label="Fırsat"><b style="color:' + (r.opportunity >= 70 ? 'var(--accent-green)' : r.opportunity >= 50 ? '#f59e0b' : 'var(--text-muted)') + ';">' + r.opportunity + '</b></td>' +
            '</tr>';
    }).join('');
}

// GİRİŞ görünürken 90 sn'de bir tazele
setInterval(() => {
    const w = document.getElementById('dashboard-wrapper');
    if (w && w.style.display !== 'none') fetchDipBreakout();
}, 90000);
setTimeout(fetchDipBreakout, 4000);

// ========== SIRALAMA (LEADERBOARD) ==========
async function fetchLeaderboard() {
    const tbody = document.getElementById('lb-tbody');
    if (!tbody) return;
    try {
        const res = await fetch('/api/leaderboard?t=' + Date.now());
        const data = await res.json();
        if (data.status !== 'success') {
            tbody.innerHTML = '<tr><td colspan="6" style="text-align:center; color:var(--accent-red);">Hata: ' + (data.message || '') + '</td></tr>';
            return;
        }
        const rows = data.leaderboard || [];
        if (!rows.length) {
            tbody.innerHTML = '<tr><td colspan="6" style="text-align:center; color:var(--text-muted);">Henüz kayıtlı kullanıcı yok.</td></tr>';
            return;
        }
        const medals = {1: '🥇', 2: '🥈', 3: '🥉'};
        tbody.innerHTML = '';
        rows.forEach(r => {
            const pnlColor = r.open_pnl > 0 ? 'var(--accent-green)' : (r.open_pnl < 0 ? 'var(--accent-red)' : 'var(--text-muted)');
            const isMe = r.owner === (window.__vrOwnerKey || '');
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td style="text-align:center; font-weight:800; font-size:1rem;">${medals[r.rank] || r.rank}</td>
                <td style="font-weight:600; color:var(--text-light);">${r.name}${isMe ? ' <span style="font-size:0.65rem; color:var(--accent-yellow); border:1px solid rgba(250,204,21,0.5); border-radius:4px; padding:1px 5px;">SİZ</span>' : ''}</td>
                <td style="text-align:right; font-weight:800; color:var(--accent-green);">${r.equity.toLocaleString('tr-TR', {minimumFractionDigits: 2, maximumFractionDigits: 2})} ₺</td>
                <td style="text-align:right;">${r.cash.toLocaleString('tr-TR', {maximumFractionDigits: 0})} ₺</td>
                <td style="text-align:right;">${r.invested.toLocaleString('tr-TR', {maximumFractionDigits: 0})} ₺</td>
                <td style="text-align:right; font-weight:700; color:${pnlColor};">${(r.open_pnl >= 0 ? '+' : '') + r.open_pnl.toLocaleString('tr-TR', {minimumFractionDigits: 2, maximumFractionDigits: 2})} ₺</td>`;
            tbody.appendChild(tr);
        });
    } catch (e) {
        tbody.innerHTML = '<tr><td colspan="6" style="text-align:center; color:var(--accent-red);">Bağlantı hatası</td></tr>';
    }
}

// ========== SEMBOL OTOMATİK DOLDURMA + ANLIK FİYAT (Portföy Terminali) ==========
let _ltQuoteTimer = null;
let _ltAcTimer = null;
let _ltCurrentQuote = null;

let _ltSyncing = false;

function ltUpdateQty() {
    const q = _ltCurrentQuote;
    const box = document.getElementById('lt-quote-box');
    if (!box || box.style.display === 'none' || !q || !q.price) return;
    const alloc = parseFloat(document.getElementById('lt-allocation').value) || 0;
    const lot = Math.floor(alloc / q.price);
    const el = document.getElementById('lq-qty');
    const est = document.getElementById('lq-est');
    if (el) el.textContent = lot > 0 ? lot.toLocaleString('tr-TR') : '0';
    if (est) est.textContent = lot > 0
        ? `≈ ${(lot * q.price).toLocaleString('tr-TR', {maximumFractionDigits: 2})} ₺`
        : 'Tutar bu fiyata 1 lot bile etmiyor';
    // ADET alanini da senkronize et (donguye girmeyecek)
    const qtyInput = document.getElementById('lt-qty');
    if (qtyInput && document.activeElement !== qtyInput) qtyInput.value = lot > 0 ? lot : '';
}

function ltOnQtyInput() {
    const q = _ltCurrentQuote;
    if (!q || !q.price || _ltSyncing) return;
    _ltSyncing = true;
    const qty = parseInt(document.getElementById('lt-qty').value, 10);
    const allocInput = document.getElementById('lt-allocation');
    if (qty > 0 && allocInput) allocInput.value = Math.round(qty * q.price * 100) / 100;
    ltUpdateQty();
    _ltSyncing = false;
}

async function ltFetchQuote(sym) {
    const box = document.getElementById('lt-quote-box');
    if (!box) return;
    if (!sym) { box.style.display = 'none'; _ltCurrentQuote = null; return; }
    try {
        const res = await fetch('/api/quote?symbol=' + encodeURIComponent(sym));
        const q = await res.json().catch(() => ({}));
        if (!res.ok || q.status !== 'success') {
            // Gecersiz/eksik sembol: karisiklik olusturmamak icin kutuyu gizle
            box.style.display = 'none';
            _ltCurrentQuote = null;
            return;
        }
        _ltCurrentQuote = q;
        box.style.display = 'flex';
        document.getElementById('lq-symbol').textContent = q.symbol;
        document.getElementById('lq-price').textContent = q.price.toLocaleString('tr-TR', {minimumFractionDigits: 2, maximumFractionDigits: 2});
        const chEl = document.getElementById('lq-change');
        const up = q.change_pct >= 0;
        chEl.textContent = (up ? '+' : '') + q.change_pct.toFixed(2) + '%';
        chEl.style.color = up ? 'var(--accent-green)' : 'var(--accent-red)';
        ltUpdateQty();
    } catch (e) {
        box.style.display = 'none';
        _ltCurrentQuote = null;
    }
}

function ltOnSymbolInput() {
    const input = document.getElementById('lt-symbol');
    const dd = document.getElementById('lt-ac-dropdown');
    const q = input.value.trim().toUpperCase();
    clearTimeout(_ltAcTimer);
    clearTimeout(_ltQuoteTimer);

    // Kullanici yazarken Onceki quote'u gecersiz kil
    _ltCurrentQuote = null;

    if (!q) { if (dd) dd.style.display = 'none'; return; }

    // Fiyat (yazmayi biraktiktan 450ms sonra)
    _ltQuoteTimer = setTimeout(() => ltFetchQuote(q), 450);

    // Otomatik doldurma listesi (temiz: hisselerOnce, varantlar ayri baslikla)
    _ltAcTimer = setTimeout(async () => {
        try {
            const res = await fetch('/api/autocomplete?grouped=1&q=' + encodeURIComponent(q));
            const data = await res.json();
            if (!dd) return;
            dd.innerHTML = '';
            const stocks = Array.isArray(data) ? data : (data.stocks || []);
            const warrants = Array.isArray(data) ? [] : (data.warrants || []);
            if (!stocks.length && !warrants.length) { dd.style.display = 'none'; return; }

            const mkItem = (title, sub, sym) => {
                const item = document.createElement('div');
                item.style.cssText = 'padding:7px 12px; cursor:pointer; font-size:0.88rem; color:var(--text-main); display:flex; justify-content:space-between; align-items:center; gap:10px; border-bottom:1px solid rgba(255,255,255,0.04);';
                item.onmouseenter = () => item.style.background = 'rgba(255,255,255,0.06)';
                item.onmouseleave = () => item.style.background = 'transparent';
                item.onclick = () => {
                    input.value = sym;
                    dd.style.display = 'none';
                    ltFetchQuote(sym);
                    input.focus();
                };
                const t = document.createElement('span');
                t.textContent = title;
                t.style.fontWeight = '600';
                item.appendChild(t);
                if (sub) {
                    const sEl = document.createElement('span');
                    sEl.textContent = sub;
                    sEl.style.cssText = 'font-size:0.7rem; color:var(--accent-purple); border:1px solid rgba(168,85,247,0.4); border-radius:4px; padding:1px 6px;';
                    item.appendChild(sEl);
                }
                dd.appendChild(item);
            };

            stocks.forEach(s => mkItem(s, '', s));
            if (warrants.length) {
                const head = document.createElement('div');
                head.textContent = 'VARANTLAR';
                head.style.cssText = 'padding:5px 12px 3px; font-size:0.65rem; letter-spacing:1px; color:var(--text-muted); background:rgba(0,0,0,0.3);';
                dd.appendChild(head);
                warrants.forEach(w => mkItem(w.label, 'VARANT', w.symbol));
            }
            dd.style.display = 'block';
        } catch (e) { if (dd) dd.style.display = 'none'; }
    }, 180);
}

// Sembol kutusunu bagla (Portfoy sekmesinde varsa)
(function () {
    const input = document.getElementById('lt-symbol');
    if (!input) return;
    input.addEventListener('input', ltOnSymbolInput);
    input.addEventListener('blur', () => {
        setTimeout(() => {
            const dd = document.getElementById('lt-ac-dropdown');
            if (dd) dd.style.display = 'none';
        }, 200);
    });
    const alloc = document.getElementById('lt-allocation');
    if (alloc) alloc.addEventListener('input', () => {
        if (_ltSyncing) return;
        _ltSyncing = true;
        ltUpdateQty();
        _ltSyncing = false;
    });
    const qtyInput = document.getElementById('lt-qty');
    if (qtyInput) qtyInput.addEventListener('input', ltOnQtyInput);
})();

// ========== PORTFÖY SIFIRLAMA TALEBİ + YÖNETİCİ PANELİ ==========
async function ltResetRequest() {
    if (!confirm('Portföy sıfırlama talebi yöneticiye gönderilecek.\n\nOnaylanırsa: tüm pozisyonlarınız ve işlem geçmişiniz silinir, bakiyeniz 100.000 ₺ olur.\n\nDevam edilsin mi?')) return;
    try {
        const res = await fetch('/api/portfolio/reset_request', {method: 'POST'});
        const data = await res.json();
        alert(data.message || (data.status === 'success' ? 'Talep gönderildi' : 'Hata'));
        ltRefreshResetUI();
    } catch (e) {
        alert('Bağlantı hatası');
    }
}

async function ltRefreshResetUI() {
    try {
        const res = await fetch('/api/portfolio/reset_status?t=' + Date.now());
        const data = await res.json();
        const btn = document.getElementById('lt-reset-btn');
        if (!btn) return;
        if (data.last_request === 'PENDING') {
            btn.disabled = true;
            btn.innerHTML = '<i class="fa-solid fa-hourglass-half"></i> Talep beklemede';
        } else {
            btn.disabled = false;
            btn.innerHTML = '<i class="fa-solid fa-rotate-left"></i> Portföyü Sıfırla';
        }
    } catch (e) { /* sessiz */ }
}

async function fetchAdminResetRequests() {
    const wrap = document.getElementById('lt-admin-panel');
    if (!wrap) return;
    try {
        const res = await fetch('/api/admin/reset_requests?t=' + Date.now());
        if (res.status === 403) { wrap.style.display = 'none'; return; }
        const data = await res.json();
        if (data.status !== 'success') { wrap.style.display = 'none'; return; }
        wrap.style.display = 'block';
        const tbody = document.getElementById('lt-admin-tbody');
        if (!tbody) return;
        tbody.innerHTML = '';
        const reqs = data.requests || [];
        if (reqs.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" style="text-align:center; color:var(--text-muted);">Bekleyen talep yok.</td></tr>';
        } else {
            reqs.forEach(r => {
                const tr = document.createElement('tr');
                const who = r.email || r.display_name || r.owner_key;
                tr.innerHTML = `
                    <td style="font-weight:bold; color:var(--text-light);">${who}</td>
                    <td style="font-size:0.75rem; color:var(--text-muted);">${r.owner_key}</td>
                    <td>${(r.created_at || '').slice(5, 16)}</td>
                    <td>
                        <button onclick="ltAdminDecide(${r.id}, 'approve')" style="background:rgba(16,185,129,0.15); border:1px solid var(--accent-green); color:var(--accent-green); border-radius:6px; padding:4px 10px; cursor:pointer; font-size:0.78rem; font-weight:bold;">Onayla</button>
                        <button onclick="ltAdminDecide(${r.id}, 'reject')" style="background:rgba(225,29,72,0.15); border:1px solid var(--accent-red); color:var(--accent-red); border-radius:6px; padding:4px 10px; cursor:pointer; font-size:0.78rem; font-weight:bold;">Reddet</button>
                    </td>`;
                tbody.appendChild(tr);
            });
        }
    } catch (e) { /* sessiz */ }
}

async function ltAdminDecide(id, action) {
    if (!confirm(action === 'approve'
        ? 'Bu kullanıcının portföyü TAMAMEN SIFIRLANACAK (pozisyonlar, işlem geçmişi; bakiye 100.000 ₺). Onaylıyor musunuz?'
        : 'Bu sıfırlama talebi reddedilsin mi?')) return;
    try {
        const res = await fetch('/api/admin/reset_requests/decide', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({id: id, action: action})
        });
        const data = await res.json();
        alert(data.message || (data.status === 'success' ? 'Tamam' : 'Hata'));
        fetchAdminResetRequests();
        fetchLiveTerminal();
    } catch (e) {
        alert('Bağlantı hatası');
    }
}

function renderEquityCurveChart(equityData) {
    const ctx = document.getElementById('equityCurveChart');
    if (!ctx) return;
    
    if (equityChartInstance) {
        equityChartInstance.destroy();
    }
    
    const labels = equityData.map(d => d.date_str);
    const dataPoints = equityData.map(d => d.end_equity);
    
    equityChartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Bakiye (₺)',
                data: dataPoints,
                borderColor: '#3b82f6',
                backgroundColor: 'rgba(59, 130, 246, 0.1)',
                borderWidth: 2,
                pointRadius: 3,
                pointBackgroundColor: '#3b82f6',
                fill: true,
                tension: 0.2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    callbacks: {
                        label: function(context) {
                            let label = context.dataset.label || '';
                            if (label) {
                                label += ': ';
                            }
                            if (context.parsed.y !== null) {
                                label += new Intl.NumberFormat('tr-TR', { style: 'currency', currency: 'TRY' }).format(context.parsed.y);
                            }
                            return label;
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: {
                        color: 'rgba(255, 255, 255, 0.05)'
                    },
                    ticks: {
                        color: '#94a3b8'
                    }
                },
                y: {
                    grid: {
                        color: 'rgba(255, 255, 255, 0.05)'
                    },
                    ticks: {
                        color: '#94a3b8',
                        callback: function(value, index, values) {
                            return value.toLocaleString('tr-TR');
                        }
                    }
                }
            }
        }
    });
}

function renderDailyBreakdown(dailyList, tbody, prefix = '') {
    if (!tbody) return;
    const weekVal = document.getElementById('stats-tab-week-select')?.value;
    let expectedDates = [];
    if (weekVal) {
        const [year, weekStr] = weekVal.split('-W');
        const simple = new Date(year, 0, 1 + (weekStr - 1) * 7);
        const dow = simple.getDay();
        const ISOweekStart = simple;
        if (dow <= 4)
            ISOweekStart.setDate(simple.getDate() - simple.getDay() + 1);
        else
            ISOweekStart.setDate(simple.getDate() + 8 - simple.getDay());
        for(let i = 0; i < 5; i++) {
            const d = new Date(ISOweekStart);
            d.setDate(d.getDate() + i);
            expectedDates.push(d.toISOString().slice(0, 10));
        }
    } else {
        expectedDates = dailyList.map(d => d.date);
    }
    if (expectedDates.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="text-muted text-center" style="padding:2rem;">Bu hafta icin kayit bulunamadi.</td></tr>';
        return;
    }
    tbody.innerHTML = '';
    // Reverse SİLİNDİ, en yeni tarih en üstte çıksın
    expectedDates.forEach(dateStr => {
        const d = dailyList.find(x => x.date === dateStr);
        if (!d) {
            const tr = document.createElement('tr');
            tr.innerHTML = '<td><div style="font-weight:800; font-size:0.9rem; color:var(--text-light); display:flex; align-items:center; gap:6px;"><i class="fa-regular fa-calendar" style="color:var(--text-muted);"></i> ' + dateStr + '</div></td><td colspan="5" class="text-center" style="color:var(--text-muted); font-size:0.85rem; font-style:italic; padding:1.5rem 0;"><i class="fa-solid fa-mug-hot" style="font-size:1.2rem; color:rgba(255,255,255,0.1); margin-right:8px;"></i> TATİL / VERİ YOK</td>';
            tbody.appendChild(tr);
            return;
        }
        const tr = document.createElement('tr');
        const total = d.total_candidates || 0;
        const tavan = d.hit_ceiling_count || 0;
        let tavanRate = d.hit_ceiling_pct || 0;
        const avgMax = d.avg_max_gain_pct || 0;
        const avgClose = d.avg_closing_gain_pct || 0;
        const starStock = d.star_stock || 'Yok';
        const warrantCode = d.star_warrant || 'Yok';
        const warrantGain = d.star_warrant_gain || '+0%';
        
        const dailyResultColor = avgClose > 0 ? '#10b981' : (avgClose < 0 ? '#ef4444' : 'var(--text-muted)');
        const closeSign = avgClose > 0 ? '+' : '';
        const maxSign = avgMax > 0 ? '+' : '';
        
        tr.innerHTML = `
            <td>
                <div style="font-weight:800; font-size:0.9rem; color:var(--text-light); display:flex; align-items:center; gap:6px;">
                    <i class="fa-regular fa-calendar-check" style="color:#10b981;"></i> ${d.date}
                </div>
                <div style="font-size:0.65rem; color:#10b981; font-weight:700; margin-top:3px;">
                    <i class="fa-solid fa-check"></i> ${d.status === 'COMPLETED' ? 'Tamamlandı' : 'Canlı'}
                </div>
            </td>
            <td>
                <div style="font-size:1.1rem; font-weight:800; color:#fff;">${total}</div>
            </td>
            <td>
                <div style="font-size:0.9rem; font-weight:800; color:#10b981;">%${tavanRate} Başarı</div>
                <div style="font-size:0.72rem; color:var(--text-muted); margin-top:2px;">${tavan}/${total} Hisse Tavana Ulaştı</div>
            </td>
            <td>
                <div style="font-weight:800; font-size:0.9rem; color:${dailyResultColor};">${closeSign}${avgClose.toFixed(2)}%</div>
                <div style="font-size:0.72rem; color:var(--accent-yellow); font-weight:600;">Zirve: ${maxSign}${avgMax.toFixed(2)}%</div>
            </td>
            <td>
                <div style="font-weight:800; font-size:0.85rem; color:#38bdf8;">${starStock}</div>
                <div style="font-size:0.72rem; color:#c084fc; font-weight:700; margin-top:2px;">${warrantCode} ${warrantGain}</div>
            </td>
            <td>
                <button onclick="console.log('Detayları Ac clicked for ${d.date}'); openTavanAuditForDate('${d.date}')" class="btn-primary" style="background:rgba(239,68,68,0.25); color:#fca5a5; border:1px solid rgba(239,68,68,0.4); padding:4px 10px; font-size:0.8rem; font-weight:bold; border-radius:4px; cursor:pointer; display:flex; align-items:center; gap:6px;">
                    <i class="fa-solid fa-folder-open"></i> Detayları Aç
                </button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}


async function fetchLiveOrders() {
    const container = document.getElementById('live-orders-container');
    if (!container) return;
    
    try {
        const res = await fetch(`/api/simulation/live_orders?t=${Date.now()}`);
        const data = await res.json();
        
        if (data.status === 'success' && data.orders && data.orders.length > 0) {
            container.innerHTML = '';
            data.orders.forEach(order => {
                let card = document.createElement('div');
                card.style.cssText = "background:var(--bg-card); border:1px solid var(--border-color); border-radius:8px; padding:1rem; display:flex; flex-direction:column; gap: 0.5rem;";
                
                card.innerHTML = `
                    <div style="display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid var(--border-color); padding-bottom:0.5rem; margin-bottom:0.5rem;">
                        <strong style="color:var(--text-light); font-size:1.1rem;"><i class="fa-solid fa-crosshairs text-blue"></i> ${order.symbol}</strong>
                        <span style="background:var(--accent-blue); color:#fff; font-size:0.75rem; padding:0.1rem 0.4rem; border-radius:4px;">Güç: ${order.score}</span>
                    </div>
                    <div style="display:flex; justify-content:space-between; font-size:0.9rem;">
                        <span style="color:var(--text-muted);">Alış Fiyatı:</span>
                        <strong style="color:var(--text-main);">₺${order.entry_price.toFixed(2)}</strong>
                    </div>
                    <div style="display:flex; justify-content:space-between; font-size:0.9rem;">
                        <span style="color:var(--text-muted);">Miktar (Lot):</span>
                        <strong style="color:var(--text-main); font-family:monospace;">${order.shares} Lot</strong>
                    </div>
                    <div style="background:rgba(255,255,255,0.02); padding:0.5rem; border-radius:4px; margin-top:0.5rem;">
                        <div style="font-size:0.8rem; color:var(--accent-yellow); margin-bottom:0.3rem;"><i class="fa-solid fa-link"></i> <strong>Zincir Emirler (OCO)</strong></div>
                        <div style="display:flex; justify-content:space-between; font-size:0.85rem; margin-bottom:0.2rem;">
                            <span style="color:var(--accent-red);">Stop-Loss (-%3):</span>
                            <strong>₺${order.stop_price.toFixed(2)}</strong>
                        </div>
                        <div style="display:flex; justify-content:space-between; font-size:0.85rem; margin-bottom:0.2rem;">
                            <span style="color:var(--accent-green);">Kâr Al TP1 (+%5):</span>
                            <strong>₺${order.tp1_price.toFixed(2)}</strong>
                        </div>
                        <div style="display:flex; justify-content:space-between; font-size:0.85rem;">
                            <span style="color:var(--accent-green);">Kâr Al TP2 (Tavan):</span>
                            <strong>₺${order.tp2_price.toFixed(2)}</strong>
                        </div>
                    </div>
                `;
                container.appendChild(card);
            });
        } else {
            container.innerHTML = '<div style="color:var(--text-muted);"><i class="fa-solid fa-circle-exclamation"></i> Bugün için geçerli "Çelik Emir" kriterlerine uyan sinyal bulunamadı.</div>';
        }
    } catch (e) {
        container.innerHTML = '<div style="color:var(--accent-red);">Hata: ' + e.message + '</div>';
    }
}




// ========== BACKTEST ENGINE ==========
async function runBacktest() {
    const symbol = document.getElementById('bt-symbol').value || 'THYAO';
    const strategy = document.getElementById('bt-strategy').value;
    const capital = document.getElementById('bt-capital').value;
    const period = document.getElementById('bt-period').value;
    
    let trailingStop = 0.0;
    const tsEl = document.getElementById('bt-trailing-stop');
    if (tsEl) trailingStop = parseFloat(tsEl.value) || 0.0;
    
    let stopLoss = 0.0;
    const slEl = document.getElementById('bt-stop-loss');
    if (slEl) stopLoss = parseFloat(slEl.value) || 0.0;
    
    // Set interval based on period
    const interval = period === '1mo' ? '1h' : '1d';
    
    const loading = document.getElementById('bt-loading');
    const results = document.getElementById('bt-results');
    const btn = document.getElementById('btn-run-backtest');
    
    loading.style.display = 'block';
    results.style.display = 'none';
    btn.disabled = true;
    
    try {
        const response = await fetch(`/api/backtest/run?symbol=${symbol}&strategy=${strategy}&capital=${capital}&period=${period}&interval=${interval}&trailing_stop=${trailingStop}&stop_loss=${stopLoss}`);
        const data = await response.json();
        
        loading.style.display = 'none';
        btn.disabled = false;
        
        if (data.status !== 'success') {
            alert('Backtest Hatası: ' + data.message);
            return;
        }
        
        results.style.display = 'block';
        
        // Fill metrics
        const bt = data.backtest;
        const mc = data.monte_carlo;
        
        const pnlPct = ((bt.final_capital - capital) / capital) * 100;
        document.getElementById('bt-res-pnl').textContent = '%' + pnlPct.toFixed(2);
        document.getElementById('bt-res-pnl').style.color = pnlPct >= 0 ? 'var(--accent-green)' : 'var(--accent-red)';
        
        document.getElementById('bt-res-winrate').textContent = '%' + bt.win_rate.toFixed(1);
        document.getElementById('bt-res-dd').textContent = '%' + bt.max_drawdown.toFixed(2);
        document.getElementById('bt-res-var').textContent = '%' + mc.VaR_99.toFixed(2);
        
        // Equity Chart
        const equityOptions = {
            series: [{ name: 'Portföy (TL)', data: bt.equity_curve }],
            chart: { type: 'area', height: 400, toolbar: { show: false }, background: 'transparent' },
            colors: ['#8b5cf6'],
            fill: { type: 'gradient', gradient: { shadeIntensity: 1, opacityFrom: 0.4, opacityTo: 0.05, stops: [0, 100] } },
            dataLabels: { enabled: false },
            stroke: { curve: 'smooth', width: 2 },
            xaxis: { type: 'category', categories: bt.dates, labels: { style: { colors: '#94a3b8' } } },
            yaxis: { labels: { style: { colors: '#94a3b8' }, formatter: (val) => val.toFixed(0) + ' TL' } },
            theme: { mode: 'dark' }
        };
        
        if(window.equityChart) window.equityChart.destroy();
        window.equityChart = new ApexCharts(document.querySelector('#bt-equity-chart'), equityOptions);
        window.equityChart.render();
        
        // Monte Carlo Histogram (Simplified as Line Chart for 10 random paths)
        const mcPaths = mc.simulated_paths.slice(0, 10);
        const mcSeries = mcPaths.map((path, idx) => ({ name: 'Senaryo ' + (idx+1), data: path }));
        
        const mcOptions = {
            series: mcSeries,
            chart: { type: 'line', height: 300, toolbar: { show: false }, background: 'transparent', animations: { enabled: false } },
            stroke: { curve: 'straight', width: 1 },
            dataLabels: { enabled: false },
            xaxis: { labels: { show: false } },
            yaxis: { labels: { style: { colors: '#94a3b8' } } },
            legend: { show: false },
            theme: { mode: 'dark' }
        };
        
        if(window.mcChart) window.mcChart.destroy();
        window.mcChart = new ApexCharts(document.querySelector('#bt-mc-chart'), mcOptions);
        window.mcChart.render();
        
    } catch (err) {
        console.error(err);
        loading.style.display = 'none';
        btn.disabled = false;
        alert('Sunucu hatası: ' + err.message);
    }
}// ========== BACKTEST AUTOCOMPLETE LOGIC ==========
const btSymbolInput = document.getElementById('bt-symbol');
const btAcDropdown = document.getElementById('bt-ac-dropdown');
let btAcTimeout = null;
let btAcSelectedIndex = -1;
let btAcItems = [];

function updateBtAcSelection() {
    btAcItems.forEach((item, index) => {
        if (index === btAcSelectedIndex) {
            item.classList.add('active');
            item.scrollIntoView({ block: 'nearest' });
        } else {
            item.classList.remove('active');
        }
    });
}

if (btSymbolInput && btAcDropdown) {
    btSymbolInput.addEventListener('input', function() {
        clearTimeout(btAcTimeout);
        const q = this.value.trim();
        btAcSelectedIndex = -1;
        if (q.length < 1) { btAcDropdown.style.display = 'none'; return; }
        
        btAcTimeout = setTimeout(async () => {
            try {
                const res = await fetch('/api/autocomplete?q=' + q);
                const matches = await res.json();
                if (matches.length === 0) { btAcDropdown.style.display = 'none'; return; }
                
                btAcDropdown.innerHTML = '';
                btAcItems = [];
                matches.forEach((m, index) => {
                    let div = document.createElement('div');
                    div.className = 'ac-item';
                    div.innerText = m;
                    div.dataset.index = index;
                    div.onclick = function() {
                        btSymbolInput.value = m;
                        btAcDropdown.style.display = 'none';
                    };
                    btAcItems.push(div);
                    btAcDropdown.appendChild(div);
                });
                btAcDropdown.style.display = 'block';
            } catch(e) { btAcDropdown.style.display = 'none'; }
        }, 200);
    });

    document.addEventListener('click', function(e) {
        if (!e.target.closest('#backtest-wrapper .search-container')) btAcDropdown.style.display = 'none';
    });

    btSymbolInput.addEventListener('keydown', function(event) {
        if (btAcDropdown.style.display === 'block' && btAcItems.length > 0) {
            if (event.key === 'ArrowDown') {
                event.preventDefault();
                btAcSelectedIndex++;
                if (btAcSelectedIndex >= btAcItems.length) btAcSelectedIndex = 0;
                updateBtAcSelection();
            } else if (event.key === 'ArrowUp') {
                event.preventDefault();
                btAcSelectedIndex--;
                if (btAcSelectedIndex < 0) btAcSelectedIndex = btAcItems.length - 1;
                updateBtAcSelection();
            } else if (event.key === 'Enter') {
                event.preventDefault();
                if (btAcSelectedIndex > -1 && btAcSelectedIndex < btAcItems.length) {
                    btSymbolInput.value = btAcItems[btAcSelectedIndex].innerText;
                }
                btAcDropdown.style.display = 'none';
            }
        }
    });
}


// --- MTF SCANNER LOGIC ---
async function loadMTFRadar() {
    const tbody = document.getElementById('mtf-table-body');
    const countBadge = document.getElementById('mtf-count');
    const loading = document.getElementById('mtf-loading');
    
    // Show only MTF card
    document.querySelectorAll('#radar-cards-grid > .card').forEach(c => c.style.display = 'none');
    document.getElementById('mtf-card').style.display = 'flex';
    
    tbody.innerHTML = '';
    loading.style.display = 'block';
    
    try {
        const response = await fetch('/api/scan_mtf');
        const data = await response.json();
        
        loading.style.display = 'none';
        
        if (data.status === 'success') {
            countBadge.innerText = data.count + ' HİSSE';
            if (data.count === 0) {
                tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; padding:20px; color:var(--text-muted);">Şu an MTF kriterlerine uyan hisse bulunamadı.</td></tr>';
                return;
            }
            
            data.results.forEach(res => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td><strong style="color:var(--text-light);">${res.Symbol}</strong></td>
                    <td>
                        <div class="progress-bar"><div class="fill" style="width: ${res.Score}%; background: linear-gradient(90deg, #0284c7, #38bdf8);"></div></div>
                        <div style="font-size:0.75rem; text-align:right; margin-top:2px; color:var(--text-muted);">${res.Score.toFixed(1)} / 100</div>
                    </td>
                    <td>
                        <div style="font-weight:bold; color:var(--text-light);">${res.Price.toFixed(2)}</div>
                        <div style="font-size:0.75rem; color:#10b981;">Hedef: ${res.Target.toFixed(2)}</div>
                    </td>
                    <td>
                        <span class="status-badge status-positive" style="background:rgba(14,165,233,0.1); color:#38bdf8; border:1px solid rgba(56,189,248,0.3);">${res.Momentum}</span>
                    </td>
                    <td>
                        <button class="btn-primary" onclick="analyzeSymbol('${res.Symbol}')" style="padding:5px 10px; font-size:0.8rem; background:rgba(30,41,59,0.8); border:1px solid rgba(255,255,255,0.1);"><i class="fa-solid fa-microscope"></i> Analiz</button>
                    </td>
                `;
                tbody.appendChild(tr);
            });
        } else {
            tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; color:var(--accent-red);">Hata: ' + data.message + '</td></tr>';
        }
    } catch (e) {
        loading.style.display = 'none';
        tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; color:var(--accent-red);">Bağlantı hatası: ' + e.message + '</td></tr>';
    }
}
// --- END MTF SCANNER LOGIC ---



async function fetchLogs() {
    const container = document.getElementById('log-container');
    if (!container) return;
    container.innerHTML = 'Yükleniyor...';
    try {
        const res = await fetch('/api/logs?t=' + Date.now());
        const data = await res.json();
        if (data.status === 'success') {
            container.innerHTML = data.logs || 'Kayıt bulunamadı.';
            container.scrollTop = container.scrollHeight;
        } else {
            container.innerHTML = `<span style="color:var(--accent-red)">Hata: ${data.message}</span>`;
        }
    } catch (err) {
        container.innerHTML = `<span style="color:var(--accent-red)">Bağlantı hatası: ${err}</span>`;
    }
}


// ==========================================
// V8 ENGINE INTEGRATION
// ==========================================
const V8_API = '/api/v8';
let v8Interval = null;

function formatV8Price(entry, current) {
    if (!entry || !current) return "-";
    const chg = ((current - entry) / entry) * 100;
    const color = chg > 0 ? "color:var(--accent-green)" : (chg < 0 ? "color:var(--accent-red)" : "color:var(--text-muted)");
    const sign = chg > 0 ? "+" : "";
    return `<span style="${color}">${current.toFixed(2)} (${sign}${chg.toFixed(2)}%)</span>`;
}

function loadV8Regime() {
    fetch(`${V8_API}/market/regime`)
        .then(res => res.json())
        .then(data => {
            const el = document.getElementById('regime-status');
            if(!el) return;
            el.textContent = data.regime || "UNKNOWN";
            
            let bg = "var(--bg-lighter)";
            let color = "var(--text-light)";
            if(data.regime.includes("BULL")) { bg = "rgba(16,185,129,0.2)"; color = "var(--accent-green)"; }
            if(data.regime.includes("BEAR")) { bg = "rgba(225,29,72,0.2)"; color = "var(--accent-red)"; }
            
            el.style.backgroundColor = bg;
            el.style.color = color;
            el.style.border = `1px solid ${color}`;
            
            document.getElementById('regime-score').textContent = `Güç: ${data.score || 0}/100`;
            
            const trend = parseFloat(data.xu100_trend || 0).toFixed(2);
            const trendColor = trend > 0 ? "var(--accent-green)" : "var(--accent-red)";
            document.getElementById('regime-trend').innerHTML = `BIST100 Trend: <span style="color:${trendColor}; font-weight:bold;">${trend > 0 ? '+' : ''}${trend}%</span>`;
        }).catch(e => console.error("V8 Regime Error", e));
}

function loadV8Discovery() {
    fetch(`${V8_API}/radar/discovery`)
        .then(res => res.json())
        .then(json => {
            const tbody = document.getElementById('v8-discovery-tbody');
            if(!tbody) return;
            tbody.innerHTML = '';
            
            if (!json.data || json.data.length === 0) {
                tbody.innerHTML = '<tr><td colspan="7" style="text-align:center; padding:1rem; color:var(--text-muted);">Şu an sıkışma hazırlığında olan hisse yok.</td></tr>';
                return;
            }

            json.data.slice(0, 15).forEach(d => {
                const tr = document.createElement('tr');
                let stateStyle = "color:var(--text-muted)";
                if (d.state === "READY") stateStyle = "color:var(--accent-blue); font-weight:bold;";
                if (d.state === "PREPARING") stateStyle = "color:var(--accent-green);";
                
                const tf = d.timeframe_breakdown || {};
                const short = tf.short ? tf.short.score : '-';
                const medium = tf.medium ? tf.medium.score : '-';
                const long = tf.long ? tf.long.score : '-';
                
                tr.innerHTML = `
                    <td style="font-weight:bold; color:var(--text-light);">${d.symbol}</td>
                    <td><span style="${stateStyle}">${d.state}</span></td>
                    <td style="text-align:center;">${d.preparation_score}</td>
                    <td style="text-align:center; font-size:0.8rem; color:var(--text-muted);">${short}</td>
                    <td style="text-align:center; font-size:0.8rem; color:var(--text-muted);">${medium}</td>
                    <td style="text-align:center; font-size:0.8rem; color:var(--text-muted);">${long}</td>
                    <td style="text-align:center; color:var(--accent-green);">${d.metrics.relative_volume}x</td>
                `;
                tbody.appendChild(tr);
            });
        }).catch(e => console.error(e));
}

function loadV8Breakout() {
    fetch(`${V8_API}/radar/breakout`)
        .then(res => res.json())
        .then(json => {
            const tbody = document.getElementById('v8-breakout-tbody');
            if(!tbody) return;
            tbody.innerHTML = '';
            
            if (!json.data || json.data.length === 0) {
                tbody.innerHTML = '<tr><td colspan="6" style="text-align:center; padding:1rem; color:var(--text-muted);">Aktif bir kırılım tespit edilmedi.</td></tr>';
                return;
            }

            json.data.slice(0, 15).forEach(d => {
                const tr = document.createElement('tr');
                const fakeRiskColor = d.fakeout_risk > 50 ? "var(--accent-red)" : "var(--accent-green)";
                
                let entryStyle = "color:var(--text-muted);";
                if(d.entry_status === "ENTER") entryStyle = "color:var(--accent-green); font-weight:bold; background:rgba(16,185,129,0.1); padding:2px 6px; border-radius:4px;";
                if(d.entry_status === "WAIT_PULLBACK") entryStyle = "color:var(--accent-yellow);";
                if(d.entry_status === "CHASE_RISK" || d.entry_status === "NO_ENTRY") entryStyle = "color:var(--accent-red);";
                
                const speed = d.momentum_speed || 'NORMAL';
                let speedColor = "var(--text-muted)";
                if(speed === "EXPLOSIVE") speedColor = "var(--accent-green)";
                if(speed === "STRONG") speedColor = "var(--accent-blue)";
                if(speed === "WEAK") speedColor = "var(--accent-red)";
                
                const tfq = d.timeframe_quality || 0;
                const tfqColor = tfq >= 60 ? "var(--accent-green)" : (tfq >= 40 ? "var(--accent-yellow)" : "var(--text-muted)");
                
                tr.innerHTML = `
                    <td style="font-weight:bold; color:var(--accent-green);">${d.symbol}</td>
                    <td style="font-size:0.85rem;">
                        <div style="color:var(--accent-blue)">Güç: ${d.breakout_score}</div>
                        <div style="color:${fakeRiskColor}">Tuzak: %${d.fakeout_risk}</div>
                    </td>
                    <td><span style="${entryStyle}">${d.entry_status}</span></td>
                    <td style="font-size:0.8rem; color:${speedColor}; font-weight:bold;">${speed}</td>
                    <td style="text-align:center; font-size:0.85rem; color:${tfqColor}; font-weight:bold;">${tfq}</td>
                    
                    <td style="font-size:0.8rem; color:var(--text-muted); max-width:200px; white-space:normal;">
                        <div>${d.entry_reasons[0] || '-'}</div>
                        ${d.varrant_info && d.varrant_info.status === 'VARRANT_FOUND' ? 
                          '<div style="margin-top:4px; font-size:0.75rem; color:var(--accent-purple);"><i class="fa-solid fa-bolt"></i> Varant: ' + d.varrant_info.varrant_prefix + ' (Kaldıraç: ~' + d.varrant_info.estimated_leverage + 'x)</div>' 
                          : ''}
                    </td>
    
                `;
                tbody.appendChild(tr);
            });
        }).catch(e => console.error(e));
}

function loadV8Learning() {
    fetch(`${V8_API}/learning/outcomes`)
        .then(res => res.json())
        .then(json => {
            const tbody = document.getElementById('v8-learning-tbody');
            if(!tbody) return;
            tbody.innerHTML = '';
            
            if (!json.data || json.data.length === 0) {
                tbody.innerHTML = '<tr><td colspan="14" style="text-align:center; padding:1rem; color:var(--text-muted);">Henüz V8 tarafından alınan bir pozisyon kaydı yok.</td></tr>';
                return;
            }

            json.data.forEach(d => {
                const tr = document.createElement('tr');
                const timeStr = new Date(d.timestamp).toLocaleTimeString('tr-TR', {hour: '2-digit', minute:'2-digit'});
                
                const mfeColor = d.mfe > 2.0 ? "color:var(--accent-green); font-weight:bold;" : "color:rgba(16,185,129,0.7);";
                const maeColor = d.mae < -2.0 ? "color:var(--accent-red); font-weight:bold;" : "color:rgba(225,29,72,0.7);";
                const statColor = d.status === 'ACTIVE' ? "color:var(--accent-blue);" : "color:var(--text-muted);";
                
                tr.innerHTML = `
                    <td style="font-size:0.8rem; color:var(--text-muted);">${timeStr}</td>
                    <td style="font-weight:bold;">${d.symbol}</td>
                    <td style="text-align:right;">${d.entry_price.toFixed(2)}</td>
                    <td style="text-align:right; font-size:0.85rem;">${formatV8Price(d.entry_price, d.t_3m_price)}</td>
                    <td style="text-align:right; font-size:0.85rem;">${formatV8Price(d.entry_price, d.t_5m_price)}</td>
                    <td style="text-align:right; font-size:0.85rem;">${formatV8Price(d.entry_price, d.t_10m_price)}</td>
                    <td style="text-align:right; font-size:0.85rem;">${formatV8Price(d.entry_price, d.t_15m_price)}</td>
                    <td style="text-align:right; font-size:0.85rem;">${formatV8Price(d.entry_price, d.t_30m_price)}</td>
                    <td style="text-align:right; font-size:0.85rem;">${formatV8Price(d.entry_price, d.t_60m_price)}</td>
                    <td style="text-align:right; font-size:0.85rem;">${formatV8Price(d.entry_price, d.t_120m_price)}</td>
                    <td style="text-align:right; font-size:0.85rem;">${formatV8Price(d.entry_price, d.t_240m_price)}</td>
                    <td style="text-align:right; ${mfeColor}">+${d.mfe.toFixed(2)}%</td>
                    <td style="text-align:right; ${maeColor}">${d.mae.toFixed(2)}%</td>
                    <td style="text-align:center; font-weight:bold; ${statColor}">${d.status}</td>
                `;
                tbody.appendChild(tr);
            });
        }).catch(e => console.error(e));
}

function refreshV8Data() {
    const v8wrapper = document.getElementById('v8-wrapper');
    if(v8wrapper && v8wrapper.style.display !== 'none') {
        loadV8Regime();
        loadV8Discovery();
        loadV8Breakout();
        loadV8Learning();
    }
}

// Intercept switchMainTab to initialize V8 refresh
const originalSwitchMainTab = window.switchMainTab;
if (typeof originalSwitchMainTab === 'function' && !window.v8Hooked) {
    window.v8Hooked = true;
    window.switchMainTab = function(tabId, btnElement) {
        originalSwitchMainTab(tabId, btnElement);
        
        const v8Wrapper = document.getElementById('v8-wrapper');
        if (v8Wrapper) v8Wrapper.style.display = tabId === 'v8' ? 'block' : 'none';

        if(tabId === 'v8') {
            refreshV8Data();
            if(!v8Interval) {
                v8Interval = setInterval(refreshV8Data, 15000);
            }
        } else {
            if(v8Interval) {
                clearInterval(v8Interval);
                v8Interval = null;
            }
        }
    };
}
// ==========================================

// ========== PİYASA DEDEKTİFİ ==========
let _dtRows = [];
let _dtSummary = {};
let _dtFilter = 'all';
let _dtSearchTerm = '';
let _dtPollTimer = null;
let _dtOpenSymbol = null;

function fetchDetective(attempt) {
    attempt = attempt || 0;
    const tb = document.getElementById('dt-tbody');
    fetch('/api/detective').then(r => {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
    }).then(d => {
        if (d.status === 'error') {
            if (tb) tb.innerHTML =
                `<tr><td colspan="12" style="text-align:center; color:#ef4444; padding:1.5rem;">Hata: ${d.message || 'bilinmeyen'}</td></tr>`;
            return;
        }
        if (d.status === 'building') {
            if (tb) tb.innerHTML =
                `<tr><td colspan="12" style="text-align:center; color:#f97316; padding:1.5rem;">
                    <i class="fa-solid fa-magnifying-glass fa-spin"></i> Dedektif ilk raporunu hazırlıyor (60 gunluk 5 dakikalık veri taranıyor, ~1 dk)...</td></tr>`;
            document.getElementById('dt-updated').textContent = 'ilk tarama sürüyor...';
            if (!_dtPollTimer) _dtPollTimer = setInterval(() => {
                fetch('/api/detective').then(r => r.json()).then(dd => {
                    if (dd.status === 'ok') {
                        clearInterval(_dtPollTimer); _dtPollTimer = null;
                        _dtApplyData(dd);
                    }
                }).catch(() => {});
            }, 5000);
            return;
        }
        _dtApplyData(d);
    }).catch(e => {
        if (!tb) return;
        if (attempt < 6) {
            // Ucretsiz ornek uyuma modundan uyanirken baglanti kopabilir -> otomatik tekrar dene
            tb.innerHTML = `<tr><td colspan="12" style="text-align:center; color:#f97316; padding:1.5rem;">
                <i class="fa-solid fa-satellite-dish fa-spin"></i> Sunucu uyanıyor, bağlantı yeniden deneniyor (${attempt + 1}/6)...</td></tr>`;
            setTimeout(() => fetchDetective(attempt + 1), 8000);
        } else {
            tb.innerHTML = `<tr><td colspan="12" style="text-align:center; color:#ef4444; padding:1.5rem;">
                Bağlantı hatası${e && e.message ? ' (' + e.message + ')' : ''} —
                <a href="#" onclick="fetchDetective(0); return false;" style="color:#f97316; text-decoration:underline;">Tekrar dene</a></td></tr>`;
        }
    });
}

function _dtApplyData(d) {
    _dtRows = d.rows || [];
    _dtSummary = d.summary || {};
    document.getElementById('dt-updated').textContent =
        `Son tarama: ${d.built_at || '-'} (10 dk'da bir otomatik)`;
    _dtRenderBoxes();
    _dtRenderTable();
    if (_dtOpenSymbol) dtOpenDetail(_dtOpenSymbol, false);
}

function _dtRenderBoxes() {
    const box = document.getElementById('dt-boxes');
    if (!box) return;
    const s = _dtSummary;
    const defs = [
        { key: 'anomaly', label: '🔥 ANOMALİ', color: '#ef4444', val: s.anomaly || 0 },
        { key: 'energy', label: '🧨 PATLAMA ENERJİSİ', color: '#f97316', val: s.energy || 0 },
        { key: 'quiet', label: '🐦 SESSİZ HAREKET', color: '#22c55e', val: s.quiet || 0 },
        { key: 'delayed', label: '🕰️ GECİKENLER', color: '#eab308', val: s.delayed || 0 },
        { key: 'trap', label: '🪤 TUZAK RİSKİ', color: '#a855f7', val: s.trap || 0 },
        { key: 'leader', label: '👑 LİDER', color: '#0ea5e9', val: s.leader || 0 },
        { key: 'breakout', label: '<span style="color:#0ea5e9">●</span> KIRILIM', color: '#3b82f6', val: s.breakout || 0 },
    ];
    box.innerHTML = defs.map(b => `
        <div onclick="dtSetFilter('${b.key}', document.querySelector('.dt-filter[data-f=\\'${b.key}\\']'))"
             style="cursor:pointer; background:var(--bg-lighter); border:1px solid ${b.color}55; border-radius:10px; padding:0.6rem 0.7rem; text-align:center; transition:all .15s;"
             onmouseover="this.style.transform='translateY(-2px)'" onmouseout="this.style.transform='none'">
            <div style="font-size:0.68rem; color:${b.color}; font-weight:700;">${b.label}</div>
            <div style="font-size:1.5rem; font-weight:800; color:${b.color};">${b.val} <span style="font-size:0.7rem; color:var(--text-muted);">hisse</span></div>
        </div>`).join('');
}

function dtSetFilter(f, btn) {
    _dtFilter = f;
    document.querySelectorAll('.dt-filter').forEach(b => b.classList.remove('active'));
    if (btn) btn.classList.add('active');
    _dtRenderTable();
}

function dtApplySearch() {
    const inp = document.getElementById('dt-search');
    _dtSearchTerm = (inp ? inp.value : '').trim().toLowerCase();
    const note = document.getElementById('dt-search-note');
    if (_dtSearchTerm) {
        const n = _dtFilteredRows().length;
        note.style.display = 'block';
        note.textContent = `"${_dtSearchTerm}" → ${n} hisse bulundu`;
    } else {
        note.style.display = 'none';
    }
    _dtRenderTable();
}

function dtClearSearch() {
    _dtSearchTerm = '';
    const inp = document.getElementById('dt-search');
    if (inp) inp.value = '';
    const note = document.getElementById('dt-search-note');
    if (note) note.style.display = 'none';
    _dtRenderTable();
}

function _dtMatchSearch(r, term) {
    // Dogal dil anahtar kelime esleme
    const rules = [
        { kw: ['sessiz ama', 'sessiz hazırl', 'patlamaya hazırl'], f: r2 => (r2.status === 'Hazırlık' || (r2.change_pct < 1.5 && r2.anomaly >= 55)) },
        { kw: ['kalabalığı düşük', 'kalabalik dusuk'], f: r2 => r2.crowd < 30 },
        { kw: ['yeni başlamış', 'yeni baslamis', 'hareket yaşı', 'taze'], f: r2 => r2.move_age !== null && r2.move_age <= 30 },
        { kw: ['sessiz'], f: r2 => r2.status === 'Sessiz' },
        { kw: ['hazırlık', 'hazirlik'], f: r2 => r2.status === 'Hazırlık' },
        { kw: ['kırılım', 'kirilim', 'kırılmış'], f: r2 => r2.status === 'Kırılım' || r2.confirm >= 66 },
        { kw: ['anomal'], f: r2 => r2.anomaly >= 60 },
        { kw: ['geciken', 'gecikme'], f: r2 => r2.delay >= 55 },
        { kw: ['lider'], f: r2 => r2.role === 'Lider' },
        { kw: ['uydu'], f: r2 => r2.role === 'Uydu' },
        { kw: ['tuzak'], f: r2 => r2.trap >= 55 },
        { kw: ['ucuz risk', 'düşük risk', 'dusuk risk'], f: r2 => r2.trap < 30 },
        { kw: ['fırsat', 'firsat'], f: r2 => r2.opportunity >= 70 },
    ];
    for (const rule of rules) {
        if (rule.kw.some(k => term.includes(k))) {
            if (!rule.f(r)) return false;
        }
    }
    // serbest metin: sembol/sektor/rol adı
    const free = term.replace(/sessiz|anomal[^\s]*|geciken|gecikme|lider|uydu|tuzak|kırılı[mn]|kirilim|kalabalığı düşük|kalabalik dusuk|yeni başlamış|yeni baslamis|patlamaya hazırl|sessiz ama|hazırlık|hazirlik|fırsat|firsat|düşük risk|dusuk risk|taze|hareket yaşı/g, '').trim();
    if (free) {
        const hay = `${r.symbol} ${r.sector} ${r.role} ${r.status}`.toLowerCase();
        if (!hay.includes(free)) return false;
    }
    return true;
}

function _dtFilteredRows() {
    let rows = _dtRows;
    const f = _dtFilter;
    if (f === 'anomaly') rows = rows.filter(r => r.anomaly >= 70);
    else if (f === 'energy') rows = rows.filter(r => r.energy >= 70 && r.confirm < 66);
    else if (f === 'quiet') rows = rows.filter(r => r.status === 'Hazırlık' || (r.change_pct < 1 && r.anomaly >= 60));
    else if (f === 'delayed') rows = rows.filter(r => r.delay >= 60);
    else if (f === 'trap') rows = rows.filter(r => r.trap >= 60);
    else if (f === 'leader') rows = rows.filter(r => r.role === 'Lider');
    else if (f === 'breakout') rows = rows.filter(r => r.status === 'Kırılım');
    if (_dtSearchTerm) rows = rows.filter(r => _dtMatchSearch(r, _dtSearchTerm));
    return rows;
}

function _dtBar(v, color) {
    const c = v >= 70 ? color : (v >= 40 ? '#eab308' : '#475569');
    return `<div style="display:flex; align-items:center; gap:4px;">
        <span style="min-width:24px; font-weight:700; color:${v >= 70 ? c : 'var(--text-light, #f8fafc)'};">${v}</span>
        <div style="flex:1; height:5px; background:#1e293b; border-radius:3px; overflow:hidden;">
            <div style="width:${Math.min(100, v)}%; height:100%; background:${c};"></div>
        </div></div>`;
}

const _dtStatusColors = {
    'Sessiz': '#64748b', 'Anormal': '#ef4444', 'Hazırlık': '#22c55e', 'Hareket': '#3b82f6',
    'Kırılım': '#0ea5e9', 'Hızlanıyor': '#f97316', 'Aşırı': '#dc2626', 'Dağılım': '#a855f7', 'Tuzak': '#a855f7'
};

function _dtRenderTable() {
    const tb = document.getElementById('dt-tbody');
    if (!tb) return;
    const rows = _dtFilteredRows();
    if (!rows.length) {
        tb.innerHTML = `<tr><td colspan="12" style="text-align:center; color:var(--text-muted); padding:1.5rem;">Bu filtrede hisse yok.</td></tr>`;
        return;
    }
    tb.innerHTML = rows.map(r => {
        const sc = _dtStatusColors[r.status] || '#94a3b8';
        const price = r.price === null || r.price === undefined ? '—' : Number(r.price).toFixed(2);
        const change = r.change_pct === null || r.change_pct === undefined ? null : Number(r.change_pct);
        const chg = change === null ? 'veri yok' : (change >= 0 ? `+${change.toFixed(2)}` : change.toFixed(2));
        const chgColor = change === null ? '#94a3b8' : (change >= 0 ? '#22c55e' : '#ef4444');
        const age = r.move_age !== null && r.move_age !== undefined ? `${r.move_age} dk` : '—';
        const fp = (r.fingerprint || '').split('').map(ch =>
            `<span style="color:${ch === '↑' ? '#22c55e' : ch === '↓' ? '#ef4444' : '#64748b'}; font-weight:700;">${ch}</span>`).join(' ');
        return `<tr onclick="dtOpenDetail('${r.symbol}', true)" style="border-bottom:1px solid rgba(30,41,59,0.6); cursor:pointer;"
                 onmouseover="this.style.background='rgba(249,115,22,0.06)'" onmouseout="this.style.background='none'">
            <td style="padding:0.55rem 0.4rem; font-weight:700;">${r.symbol} <span style="font-size:0.68rem; color:var(--text-muted);">${r.sector !== 'GENEL' ? r.sector : ''}</span></td>
            <td style="padding:0.55rem 0.4rem;">${price} <span style="color:${chgColor}; font-weight:600;">${change === null ? chg : `%${chg}`}</span></td>
            <td style="padding:0.55rem 0.4rem;"><span style="background:${sc}22; color:${sc}; border:1px solid ${sc}66; padding:2px 8px; border-radius:10px; font-size:0.72rem; font-weight:700;">${r.status}</span></td>
            <td style="padding:0.55rem 0.4rem;">${_dtBar(r.anomaly, '#ef4444')}</td>
            <td style="padding:0.55rem 0.4rem;">${age}</td>
            <td style="padding:0.55rem 0.4rem;">${_dtBar(r.energy, '#f97316')}</td>
            <td style="padding:0.55rem 0.4rem;">${_dtBar(r.delay, '#eab308')}</td>
            <td style="padding:0.55rem 0.4rem;">${_dtBar(r.crowd, '#38bdf8')}</td>
            <td style="padding:0.55rem 0.4rem;">${_dtBar(r.trap, '#a855f7')}</td>
            <td style="padding:0.55rem 0.4rem; font-size:0.75rem;">${r.role}</td>
            <td style="padding:0.55rem 0.4rem; font-size:0.85rem;">${fp}</td>
            <td style="padding:0.55rem 0.4rem; font-weight:800; font-size:1.05rem; color:${r.opportunity >= 85 ? '#22c55e' : r.opportunity >= 70 ? '#f97316' : r.opportunity < 55 ? '#ef4444' : 'var(--text-light, #f8fafc)'};">${r.opportunity_tag} ${r.opportunity}</td>
        </tr>`;
    }).join('');
}

function dtOpenDetail(symbol, scroll) {
    _dtOpenSymbol = symbol;
    const panel = document.getElementById('dt-panel');
    if (!panel) return;
    panel.style.display = 'block';
    panel.innerHTML = `<div class="card" style="border:1px solid rgba(249,115,22,0.35); padding:1.2rem;">
        <div style="color:var(--text-muted); padding:1rem; text-align:center;"><i class="fa-solid fa-magnifying-glass fa-spin"></i> ${symbol} dedektif dosyası açılıyor...</div></div>`;
    if (scroll) panel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    fetch(`/api/detective/detail/${encodeURIComponent(symbol)}`).then(r => r.json()).then(d => {
        if (d.status !== 'success') {
            panel.innerHTML = `<div class="card" style="border:1px solid rgba(239,68,68,0.4); padding:1rem; color:#ef4444;">
                ${d.message || 'Panel verisi alınamadı'} <button onclick="dtCloseDetail()" style="margin-left:1rem; background:none; border:none; color:var(--text-muted); cursor:pointer;">kapat</button></div>`;
            return;
        }
        _dtRenderDetail(panel, d.detail);
    }).catch(() => {
        panel.innerHTML = `<div class="card" style="padding:1rem; color:#ef4444;">Bağlantı hatası</div>`;
    });
}

function dtCloseDetail() {
    _dtOpenSymbol = null;
    const panel = document.getElementById('dt-panel');
    if (panel) { panel.style.display = 'none'; panel.innerHTML = ''; }
}

function _dtRenderDetail(panel, d) {
    const r = d.row || {};
    const tl = (d.timeline || []).map(e =>
        `<div style="display:flex; gap:0.6rem; padding:0.25rem 0; font-size:0.8rem;">
            <span style="color:#f97316; font-weight:700; min-width:48px;">${e.time}</span>
            <span>${e.kind} ${e.text}</span></div>`).join('') || '<div style="color:var(--text-muted); font-size:0.8rem;">Bugün kayda değer olay zinciri yok.</div>';

    const why = (d.why || []).map(w => `<div style="padding:0.2rem 0; font-size:0.82rem;">${w[0]} ${w[1]}</div>`).join('');

    const sim = (d.similar || []);
    const simHtml = sim.length
        ? `<table style="width:100%; border-collapse:collapse; font-size:0.8rem;">
            <thead><tr style="color:var(--text-muted); border-bottom:1px solid var(--border-color);">
            <th style="text-align:left; padding:0.3rem;">TARİH</th><th style="text-align:left; padding:0.3rem;">BENZERLİK</th><th style="text-align:left; padding:0.3rem;">SONRAKİ DÖNEM</th></tr></thead>
            <tbody>${sim.map(s => {
                const oc = s.outcome >= 0 ? '#22c55e' : '#ef4444';
                return `<tr style="border-bottom:1px solid rgba(30,41,59,0.5);">
                    <td style="padding:0.3rem;">${s.date}</td>
                    <td style="padding:0.3rem; font-weight:700;">%${s.sim}</td>
                    <td style="padding:0.3rem; color:${oc}; font-weight:700;">${s.label}: ${s.outcome >= 0 ? '+' : ''}%${s.outcome}</td></tr>`;
            }).join('')}</tbody></table>
          <div style="margin-top:0.5rem; font-size:0.82rem; font-weight:700; color:${d.bias && d.bias.startsWith('Pozitif') ? '#22c55e' : '#ef4444'};">
            📌 Geçmiş benzerlik sonucu: ${d.bias || 'Belirsiz'}</div>`
        : '<div style="color:var(--text-muted); font-size:0.8rem;">Bu davranışa benzeyen geçmiş gün bulunamadı — bugün benzersiz bir davranış.</div>';

    const ch = d.character;
    const chHtml = ch ? `
        <div style="display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:0.5rem;">
            ${[['🚀 Hızlı hareket', ch.hizli], ['💣 Ani patlama', ch.ani_patlama], ['🪤 Sahte kırılım', ch.sahte_kirilim],
               ['🔄 Retest eğilimi', ch.retest], ['📈 Trend devamı', ch.trend_devam], ['🌊 Volatilite', ch.volatilite]]
              .map(x => `<div style="background:var(--bg-lighter); border-radius:8px; padding:0.5rem 0.6rem;">
                    <div style="font-size:0.7rem; color:var(--text-muted);">${x[0]}</div>
                    <div style="font-weight:800; font-size:1.1rem; color:${x[1] >= 70 ? '#ef4444' : x[1] >= 40 ? '#eab308' : '#22c55e'};">${x[1]}</div>
                </div>`).join('')}
        </div>` : '<div style="color:var(--text-muted); font-size:0.8rem;">Karakter analizi için yeterli geçmiş yok.</div>';

    const chain = d.chain || {};
    const mem = (chain.members || []);
    const chainHtml = mem.length
        ? `<div style="font-size:0.82rem;">${mem.map(m => {
            const oc = m.change_pct >= 0 ? '#22c55e' : '#ef4444';
            return `<div style="display:flex; justify-content:space-between; padding:0.25rem 0; border-bottom:1px solid rgba(30,41,59,0.4);">
                <span><b>${m.symbol}</b> <span style="color:var(--text-muted); font-size:0.72rem;">${m.status}</span></span>
                <span style="color:${oc}; font-weight:700;">%${m.change_pct >= 0 ? '+' : ''}${m.change_pct}</span></div>`;
          }).join('')}</div>
          ${chain.next && chain.next.length ? `<div style="margin-top:0.5rem; font-size:0.82rem; color:#22c55e;">👀 <b>Sırada olabilir:</b> ${chain.next.join(', ')}</div>` : ''}`
        : '<div style="color:var(--text-muted); font-size:0.8rem;">Bu sektörde taranan başka hisse yok.</div>';

    const startPt = d.start_point ? `<span style="color:#f97316; font-weight:700;">Hareketin muhtemel başlangıcı: ${d.start_point}</span>` : '';

    panel.innerHTML = `
    <div class="card" style="border:1px solid rgba(249,115,22,0.35);">
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:0.5rem; margin-bottom:0.8rem;">
            <h3 class="card-title" style="color:#f97316; margin:0;">🔬 ${r.symbol} — DEDEKTİF PANELİ
                <span style="font-size:0.75rem; color:var(--text-muted); font-weight:400;">${r.price} TL · %${r.change_pct >= 0 ? '+' : ''}${r.change_pct} · ${r.sector} · Parmak izi: ${r.fingerprint}</span></h3>
            <button onclick="dtCloseDetail()" style="background:transparent; border:1px solid var(--border-color); color:var(--text-muted); border-radius:8px; padding:0.3rem 0.7rem; cursor:pointer;">✕ Kapat</button>
        </div>
        <div style="display:grid; grid-template-columns:repeat(auto-fit,minmax(280px,1fr)); gap:1rem;">
            <div>
                <div style="font-weight:700; margin-bottom:0.4rem; color:#f97316;">🕰️ Hareketin Hikâyesi</div>
                ${tl}
                <div style="margin-top:0.4rem;">${startPt}</div>
            </div>
            <div>
                <div style="font-weight:700; margin-bottom:0.4rem; color:#f97316;">🧩 Neden Dikkat Çekiyor?</div>
                ${why}
            </div>
            <div>
                <div style="font-weight:700; margin-bottom:0.4rem; color:#f97316;">🕵️ Aynı Geçmiş</div>
                ${simHtml}
            </div>
            <div>
                <div style="font-weight:700; margin-bottom:0.4rem; color:#f97316;">🧬 Hisse Karakteri</div>
                ${chHtml}
            </div>
            <div>
                <div style="font-weight:700; margin-bottom:0.4rem; color:#f97316;">🌊 ${chain.sector || 'Sektör'} — Hareket Zinciri</div>
                ${chainHtml}
            </div>
        </div>
    </div>`;
}
// ========== /PİYASA DEDEKTİFİ ==========
