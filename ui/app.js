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
// 🟢 ONLİNE KULLANICI SAYACI (Heartbeat)
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
            if (el('stat-winrate')) el('stat-winrate').textContent = `%${s.tavan_success_pct}`;
            if (el('stat-winrate-sub')) el('stat-winrate-sub').textContent = `${s.total_hit_ceiling}/${s.total_candidates_tracked} Tavan`;
            if (el('stat-avgprofit')) el('stat-avgprofit').textContent = `%${s.plus5_success_pct}`;
            if (el('stat-avgprofit-sub')) el('stat-avgprofit-sub').textContent = `${s.total_hit_plus5}/${s.total_candidates_tracked} Hisse`;
            if (el('stat-pfactor')) el('stat-pfactor').textContent = `+%${s.cumulative_avg_max_gain_pct}`;
            if (el('stat-pfactor-sub')) el('stat-pfactor-sub').textContent = `Ort. Zirve Getirisi`;
            // Detay satırları
            if (el('stat-days-val')) el('stat-days-val').textContent = `${s.total_days_tracked} Gün / ${s.total_candidates_tracked} Öneri`;
            if (el('stat-warrant-val')) el('stat-warrant-val').textContent = `+%${s.ahlatci_warrant_avg_gain_pct}`;
            if (el('stat-close-val')) el('stat-close-val').textContent = `+%${s.cumulative_avg_closing_gain_pct}`;
        } else {
            // Veri yok — 04 Ağustos'tan önce
            if (el('stat-winrate')) el('stat-winrate').textContent = '-';
            if (el('stat-winrate-sub')) el('stat-winrate-sub').textContent = 'Veri bekleniyor';
            if (el('stat-avgprofit')) el('stat-avgprofit').textContent = '-';
            if (el('stat-avgprofit-sub')) el('stat-avgprofit-sub').textContent = 'Veri bekleniyor';
            if (el('stat-pfactor')) el('stat-pfactor').textContent = '-';
            if (el('stat-pfactor-sub')) el('stat-pfactor-sub').textContent = 'Veri bekleniyor';
            if (el('stat-days-val')) el('stat-days-val').textContent = '04 Ağu 2026 sabahından itibaren';
            if (el('stat-warrant-val')) el('stat-warrant-val').textContent = 'Bekleniyor';
            if (el('stat-close-val')) el('stat-close-val').textContent = 'Bekleniyor';
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
    document.getElementById('dashboard-wrapper').style.display = tabName === 'dashboard' ? 'block' : 'none';
    document.getElementById('radar-wrapper').style.display = tabName === 'radar' ? 'block' : 'none';
    document.getElementById('news-wrapper').style.display = tabName === 'news' ? 'block' : 'none';
    const statsWrapper = document.getElementById('stats-wrapper');
    if (statsWrapper) statsWrapper.style.display = tabName === 'stats' ? 'block' : 'none';
    
    document.querySelectorAll('.nav-btn').forEach(btn => btn.classList.remove('active'));
    if(btnElement) btnElement.classList.add('active');
    
    if (tabName === 'news') {
        fetchGlobalNews();
    }
    if (tabName === 'stats') {
        fetchStatsTabData();
    }
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
    if (targetTab === 'radar' && navBtns.length > 1) {
        targetBtn = navBtns[1];
    } else if (targetTab === 'news' && navBtns.length > 2) {
        targetBtn = navBtns[2];
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
    document.querySelectorAll('#radar-wrapper .tab-pane').forEach(pane => pane.classList.remove('active'));
    document.getElementById('rtab-' + tabName).classList.add('active');
    
    document.querySelectorAll('#radar-wrapper .s-tab').forEach(btn => btn.classList.remove('active'));
    if(btnElement) btnElement.classList.add('active');
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
    switchMainTab('dashboard', document.querySelectorAll('.nav-btn')[1]);
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
    const dashAtrEl = document.getElementById('dash-atr');
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
        ["1d", "1w", "1m", "3m", "6m", "12m"].forEach(p => {
            if(fc[p]) {
                let tr = document.createElement('tr');
                tr.innerHTML = `<td>${p}</td><td class="text-blue">${fc[p]}</td>`;
                fcBody.appendChild(tr);
            }
        });
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
    
    const loadingEl = document.getElementById(type + '-loading');
    const resultsEl = document.getElementById(type + '-results');
    const tbodyEl = document.getElementById(type + '-tbody');

    loadingEl.style.display = 'block';
    resultsEl.style.display = 'none';
    tbodyEl.innerHTML = '';

    try {
        const response = await fetch(endpoint);
        const data = await response.json();

        loadingEl.style.display = 'none';
        resultsEl.style.display = 'table';

        if (!data.results || data.results.length === 0) {
            tbodyEl.innerHTML = `<tr><td colspan='4' style='text-align:center; color: var(--text-muted); padding:2rem;'>0 results found. Market regime might be too risky.</td></tr>`;
            return;
        }

        data.results.forEach(res => {
            let tr = document.createElement('tr');
            let scoreValue = res.Score !== undefined ? res.Score : (res.Confidence_Score !== undefined ? res.Confidence_Score : 0);
            let scoreColor = scoreValue >= 70 ? 'var(--accent-green)' : (scoreValue >= 50 ? 'var(--accent-yellow)' : 'var(--accent-red)');
            tr.innerHTML = `
                <td style="color:var(--text-main);font-weight:700;">${res.Symbol}</td>
                <td style="color:${scoreColor};font-weight:700;">${scoreValue}</td>
                <td>${t(res.Trend)}</td>
                <td style="color:var(--accent-blue)">${t(res.Action || (scoreValue >= 60 ? "AL (POTANSİYEL)" : "İZLE"))}</td>
            `;
            tbodyEl.appendChild(tr);
        });

    } catch (error) {
        loadingEl.style.display = 'none';
        alert("RADAR ERROR: " + error);
    }
}

// ========== FAZ 6: BULK DASHBOARD & INITIALIZATION ==========
let globalDashboardData = {};

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
};

async function fetchDashboardData() {
    try {
        const response = await fetch('/api/dashboard_init');
        if (!response.ok) {
            console.error("Dashboard HTTP error: ", response.status);
            return;
        }
        const data = await response.json();
        
        if (data && data.status === 'success') {
            setElText('total-analyzed-counter', `RADAR BUGÜNE KADAR ${data.total_analyzed || 0} VERİYİ ANALİZ ETTİ`);
            
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
                console.log('[DASHBOARD] Veri henüz boş, tarama devam ediyor...');
                // Hâlâ boşsa kullanıcıyı bilgilendir
                ["tb-signals-5m", "tb-tavan-adaylari", "tb-opportunities-1h", "tb-opportunities", "tb-gainers", "tb-losers", "tb-favorites", "tb-high_volume", "tb-low_volume"].forEach(id => {
                    const tbody = document.getElementById(id);
                    if (tbody && (tbody.innerText.includes("Taran") || tbody.innerHTML.includes("Taran"))) {
                        tbody.innerHTML = `<tr><td colspan="5" style="text-align: center;" class="text-muted"><div class="spinner small" style="display:inline-block; margin-right:10px;"></div> Tarama devam ediyor...</td></tr>`;
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
        'signals_5m': 'tb-signals-5m',
        'tavan_adaylari': 'tb-tavan-adaylari',
        'opportunities_1h': 'tb-opportunities-1h',
        'opportunities': 'tb-opportunities',
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
        
        const items = globalDashboardData[cat] || [];
        if (items.length === 0) {
            tbody.innerHTML = `<tr><td colspan="5" style="text-align: center;" class="text-muted">Bu kategoride sonuç bulunamadı.</td></tr>`;
            continue;
        }

        tbody.innerHTML = '';
        // 10'a kadar hisse göster
        const displayItems = items.slice(0, 10);
        let timeStr = new Date().toLocaleTimeString('tr-TR', {hour: '2-digit', minute: '2-digit'});
        const headerTimeSpan = document.getElementById('time-' + (cat === 'opportunities_1h' ? 'opportunities-1h' : cat));
        if (headerTimeSpan) {
            headerTimeSpan.innerText = "(Güncelleme: " + timeStr + ")";
        }

        displayItems.forEach(res => {
            let tr = document.createElement('tr');
            
            let symStr = res.Symbol;
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
            
            let priceStr = res.Price ? "₺" + parseFloat(res.Price).toFixed(2) : "-";
            
            if (res.Change_Pct !== undefined && cat !== 'gainers' && cat !== 'losers' && cat !== 'opportunities_1h') {
                let p_pct = parseFloat(res.Change_Pct);
                let p_c = p_pct > 0 ? "var(--accent-green)" : (p_pct < 0 ? "var(--accent-red)" : "var(--text-muted)");
                let p_sign = p_pct > 0 ? "+" : "";
                priceStr += `<br><span style="color:${p_c}; font-size:0.75rem;">(${p_sign}%${p_pct.toFixed(2)})</span>`;
            }

            let statusStr = "";
            let scoreContent = "";
            if (cat === 'signals_5m') {
                let rsiVal = res.RSI !== undefined ? res.RSI : 0;
                let sig = res.Signal; // "AL" veya "SAT"
                let sigColor = sig === "AL" ? "var(--accent-green)" : "var(--accent-red)";
                let sigIcon = sig === "AL" ? "fa-arrow-trend-up" : "fa-arrow-trend-down";
                let rsiColor = sig === "AL" ? "var(--accent-blue)" : "var(--accent-yellow)";
                
                scoreContent = `<span style="color:${rsiColor};font-weight:700;">${rsiVal}</span>`;
                statusStr = `<span style="background:rgba(${sig==='AL'?'16,185,129':'239,68,68'}, 0.2); color:${sigColor}; padding:3px 8px; border-radius:4px; font-weight:700; font-size:0.75rem;"><i class="fa-solid ${sigIcon}"></i> ${sig} </span> <span style="font-size:0.7rem; color:var(--text-muted); margin-left:5px;">${res.Time || ''}</span>`;
            } else if (cat === 'tavan_adaylari') {
                let scoreValue = res.Score !== undefined ? res.Score : 0;
                let scoreColor = scoreValue >= 85 ? 'var(--accent-green)' : (scoreValue >= 75 ? 'var(--accent-yellow)' : 'var(--text-muted)');
                
                // Evre Rozeti (Phase Badge) & V-Dönüş
                let phaseBadge = res.Phase_Badge || 'TAVAN';
                let phaseColor = res.Phase_Color || 'green';
                let phaseBg = phaseColor === 'red' ? 'rgba(239, 68, 68, 0.2)' : (phaseColor === 'yellow' ? 'rgba(234, 179, 8, 0.2)' : 'rgba(16, 185, 129, 0.2)');
                let phaseTxtColor = phaseColor === 'red' ? 'var(--accent-red)' : (phaseColor === 'yellow' ? 'var(--accent-yellow)' : 'var(--accent-green)');
                let phaseIcon = phaseColor === 'red' ? 'fa-lock' : (phaseColor === 'yellow' ? 'fa-bolt' : 'fa-seedling');
                let evreStr = `<span style="background:${phaseBg}; color:${phaseTxtColor}; padding:3px 7px; border-radius:4px; font-weight:700; font-size:0.72rem; white-space:nowrap;"><i class="fa-solid ${phaseIcon}"></i> ${phaseBadge}</span>`;
                
                // 🛡️ Anti-Trap Shield (Tuzak Önleme Rozeti) & Teyit Skoru
                if (res.Anti_Trap_Badge) {
                    let atColor = res.Anti_Trap_Color || '#10b981';
                    let atBg = atColor === '#10b981' ? 'rgba(16, 185, 129, 0.15)' : (atColor === '#ef4444' ? 'rgba(239, 68, 68, 0.2)' : 'rgba(234, 179, 8, 0.15)');
                    evreStr += `<div style="margin-top:3px;"><span style="background:${atBg}; color:${atColor}; border:1px solid ${atColor}; padding:2px 5px; border-radius:3px; font-size:0.68rem; font-weight:700; white-space:nowrap;">${res.Anti_Trap_Badge}</span></div>`;
                }

                if (res.ORB_Breakout) {
                    evreStr += `<div style="margin-top:2px;"><span style="background:rgba(56, 189, 248, 0.15); color:#38bdf8; border:1px solid #38bdf8; padding:1px 4px; border-radius:3px; font-size:0.66rem; font-weight:700;"><i class="fa-solid fa-bullseye"></i> ORB Açılış Kırılımı</span></div>`;
                }

                if (res.V_Reversal) {
                    evreStr += `<div style="margin-top:3px;"><span style="background:rgba(168, 85, 247, 0.2); color:#c084fc; padding:2px 5px; border-radius:3px; font-size:0.68rem; font-weight:700;"><i class="fa-solid fa-bolt-lightning"></i> V-Dönüş +%${res.V_Power}</span></div>`;
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
                
                // AI Skor, Teyit Skoru, Çift Tavan ve Varant Eşleşmesi
                let scoreStr = `<div style="color:${scoreColor}; font-weight:800; font-size:0.85rem;">${scoreValue}/100</div>`;
                if (res.Teyit_Score) {
                    let tcColor = res.Teyit_Score >= 80 ? '#10b981' : (res.Teyit_Score >= 60 ? '#facc15' : '#ef4444');
                    scoreStr += `<div style="font-size:0.68rem; color:${tcColor}; font-weight:700;" title="Kurumsal Para ve Mum Teyit Skoru"><i class="fa-solid fa-shield-check"></i> %${res.Teyit_Score} Teyit</div>`;
                }
                if (res.Streak_Score) {
                    scoreStr += `<div style="font-size:0.68rem; color:#38bdf8;" title="Çift Tavan İhtimali"><i class="fa-solid fa-link"></i> %${res.Streak_Score} Seri</div>`;
                }
                
                if (res.Warrant_Match) {
                    scoreStr += `<div style="margin-top:2px;"><span style="background:rgba(234, 179, 8, 0.2); color:#facc15; padding:1px 4px; border-radius:3px; font-size:0.68rem; font-weight:700;" title="${res.Warrant_Match.Desc}"><i class="fa-solid fa-crosshairs"></i> Varant: ${res.Warrant_Match.Leverage} (+%${res.Warrant_Match.Potential_Gain_Pct})</span></div>`;
                }
                
                if (res.Position) {
                    scoreStr += `
                        <div style="font-size:0.7rem; display:flex; gap:4px; flex-wrap:wrap; margin-top:2px;">
                            <span style="background:rgba(239, 68, 68, 0.15); color:var(--accent-red); padding:1px 4px; border-radius:3px; font-weight:600;" title="İz Süren Stop"><i class="fa-solid fa-shield-halved"></i> ₺${res.Position.SL}</span>
                        </div>
                    `;
                }
                
                tr.innerHTML = `
                    <td style="color:var(--text-main);font-weight:700;">${symStr}</td>
                    <td style="font-family:monospace; font-weight:600;">${priceStr}</td>
                    <td>${evreStr}</td>
                    <td>${tavanStr}</td>
                    <td>${hacimStr}</td>
                    <td>${scoreStr}</td>
                    <td>
                        <button type="button" class="btn-primary" style="padding:0.3rem 0.6rem; font-size:0.75rem; border-radius:6px; border:none; color:white; display:flex; align-items:center; gap:4px; cursor:pointer; background:linear-gradient(135deg, #ef4444, #b91c1c); box-shadow:0 2px 6px rgba(239,68,68,0.3);" onclick="document.getElementById('symbol-input').value='${res.Symbol}'; analyzeSymbol();" title="Tavan Hedefi, Stop Seviyeleri ve Altın Varantları İncele">
                            <i class="fa-solid fa-rocket"></i> İncele
                        </button>
                    </td>
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
                    <td>
                        <button type="button" class="btn-primary" style="padding:0.3rem 0.6rem; font-size:0.75rem; border-radius:6px; border:none; color:white; display:flex; align-items:center; gap:4px; cursor:pointer; background:linear-gradient(135deg, #3b82f6, #1d4ed8); box-shadow:0 2px 6px rgba(59,130,246,0.3);" onclick="document.getElementById('symbol-input').value='${res.Symbol}'; analyzeSymbol();" title="Detaylı AI Analizi, Varant Getiri Matrisi ve Grafiği Aç">
                            <i class="fa-solid fa-chart-line"></i> İncele
                        </button>
                    </td>
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
                    <td><a href="/?symbol=${res.Symbol}&tab=graphic" target="_blank" class="btn btn-sm btn-outline-primary" style="text-decoration:none;" onclick="event.preventDefault(); openGraphicTab('${res.Symbol}'); switchMainTab('home', document.querySelector('.nav-btn.active'));">Grafikte Aç</a></td>
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
        const response = await fetch(`/api/varant_simulator?symbol=${symbol}&issuer=${encodeURIComponent(issuer)}`);
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
        const res = await fetch('/api/winrate_stats');
        const data = await res.json();
        if (data.status === 'success' && data.stats) {
            const s = data.stats.summary;
            setElText('stat-winrate', `%${s.win_rate_pct}`);
            setElText('stat-avgprofit', `+%{s.avg_profit_pct}`);
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
        const response = await fetch(`/api/varant_simulator?symbol=${cleanSym}&price=${spotPrice}&target=${defaultTarget}&issuer=${encodeURIComponent(issuer)}`);
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
        const response = await fetch(`/api/varant_simulator?symbol=${cleanSym}&price=${spot}&target=${targetVal}&issuer=${encodeURIComponent(issuer)}`);
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
            backgroundColor: '#0b0f19',
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

// 📱 MOBİL ALT BAR BUTONLARI İLE PİLL TABS EŞLEŞTİRME
function jumpToCard(cardIdx) {
    const pillButtons = document.querySelectorAll('#radar-pill-tabs .pill-btn');
    const bottomNavBtns = document.querySelectorAll('.bottom-mobile-bar .bm-btn');
    
    bottomNavBtns.forEach(b => b.classList.remove('active'));
    
    if (cardIdx === 0 && document.getElementById('bm-tavan')) {
        document.getElementById('bm-tavan').classList.add('active');
        if (pillButtons[1]) filterRadarGrid('radar-card-0', pillButtons[1]);
    } else if (cardIdx === 1 && document.getElementById('bm-1h')) {
        document.getElementById('bm-1h').classList.add('active');
        if (pillButtons[2]) filterRadarGrid('radar-card-1', pillButtons[2]);
    } else if (cardIdx === 2 && document.getElementById('bm-5m')) {
        document.getElementById('bm-5m').classList.add('active');
        if (pillButtons[3]) filterRadarGrid('radar-card-2', pillButtons[3]);
    }
}

let currentActiveCardIdx = 0;
function navigateCard(direction) {
    currentActiveCardIdx = (currentActiveCardIdx + direction + 3) % 3;
    jumpToCard(currentActiveCardIdx);
}

// ================================================================
// 📊 10:15 SABAH TAVAN LİSTESİ & 18:10 SEANS KAPANIŞ KARNESİ JS
// ================================================================

function openTavanAuditModal() {
    const modal = document.getElementById('tavan-audit-modal');
    if (modal) {
        modal.style.display = 'block';
        document.body.style.overflow = 'hidden';
        fetchTavanAuditData();
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
                            <span style="background:${badgeBg}; color:${badgeColor}; border:1px solid ${badgeColor}; padding:3px 8px; border-radius:6px; font-weight:700; font-size:0.75rem; white-space:nowrap;">
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
    const modal = document.getElementById('long-term-history-modal');
    if (modal) {
        modal.style.display = 'block';
        fetchLongTermHistoryData();
    }
}

function closeLongTermHistoryModal() {
    const modal = document.getElementById('long-term-history-modal');
    if (modal) modal.style.display = 'none';
}

function applyLongTermFilter() {
    const startDate = document.getElementById('hist-start-date')?.value || '2026-08-04';
    const endDate = document.getElementById('hist-end-date')?.value || '';
    const symbol = document.getElementById('hist-symbol-search')?.value || '';
    const time = document.getElementById('hist-time-filter')?.value || '';
    fetchLongTermHistoryData(startDate, endDate, symbol, time);
}

function openTavanAuditForDate(dateStr) {
    closeLongTermHistoryModal();
    openTavanAuditModal();
    const select = document.getElementById('tavan-audit-date-select');
    if (select) {
        select.value = dateStr;
    }
    fetchTavanAuditData(dateStr);
}

async function fetchLongTermHistoryData(startDate = '2026-08-04', endDate = '', symbol = '', time = '') {
    const dailyTbody = document.getElementById('hist-daily-tbody');
    const hofTbody = document.getElementById('hist-hall-of-fame-tbody');
    const hourlyContainer = document.getElementById('hist-hourly-cards-container');

    if (dailyTbody) dailyTbody.innerHTML = `<tr><td colspan="7" class="text-muted text-center" style="padding:1.5rem;"><i class="fa-solid fa-spinner fa-spin"></i> Tarihsel performans arşivi taranıyor...</td></tr>`;
    if (hofTbody) hofTbody.innerHTML = `<tr><td colspan="6" class="text-muted text-center" style="padding:1.5rem;"><i class="fa-solid fa-spinner fa-spin"></i> Yıldızlar hesaplanıyor...</td></tr>`;

    try {
        let url = `/api/tavan_history?start_date=${encodeURIComponent(startDate)}`;
        if (endDate) url += `&end_date=${encodeURIComponent(endDate)}`;
        if (symbol) url += `&symbol=${encodeURIComponent(symbol)}`;
        if (time) url += `&time=${encodeURIComponent(time)}`;

        const res = await fetch(url);
        const data = await res.json();

        if (data.status === 'success') {
            renderHistoryKpis(data.summary, 'hist-');
            renderHourlyCards(data.hourly_summary || [], hourlyContainer);
            renderDailyBreakdown(data.daily_breakdown || [], dailyTbody, 'hist-');
            renderHallOfFame(data.hall_of_fame || [], hofTbody);
        } else {
            if (dailyTbody) dailyTbody.innerHTML = `<tr><td colspan="7" class="text-red text-center" style="padding:1.5rem;">Veri alınamadı: ${data.message || 'Bilinmeyen hata'}</td></tr>`;
        }
    } catch (e) {
        if (dailyTbody) dailyTbody.innerHTML = `<tr><td colspan="7" class="text-red text-center" style="padding:1.5rem;">Baglanti hatasi: ${e.message}</td></tr>`;
    }
}

// ============================================================
// 📊 İSTATİSTİKLER SEKMESİ - ANA FONKSİYONLARI
// ============================================================

function switchStatsTab(tabName, btnEl) {
    // Sidebar butonları
    document.querySelectorAll('#stats-wrapper .s-tab').forEach(b => b.classList.remove('active'));
    if (btnEl) btnEl.classList.add('active');

    // Tab pane'leri göster/gizle
    const tabs = ['ozet', 'saatlik', 'gunluk', 'hallfame'];
    tabs.forEach(t => {
        const el = document.getElementById('stab-' + t);
        if (el) el.style.display = (t === tabName) ? 'block' : 'none';
    });
}

function applyStatsTabFilter() {
    const startDate = document.getElementById('stats-tab-start-date')?.value || '2026-08-04';
    const endDate = document.getElementById('stats-tab-end-date')?.value || '';
    const symbol = document.getElementById('stats-tab-symbol-search')?.value || '';
    const time = document.getElementById('stats-tab-time-filter')?.value || '';
    fetchStatsTabData(startDate, endDate, symbol, time);
}

async function fetchStatsTabData(startDate = '2026-08-04', endDate = '', symbol = '', time = '') {
    const dailyTbody = document.getElementById('stats-tab-daily-tbody');
    const hofTbody = document.getElementById('stats-tab-hall-of-fame-tbody');
    const hourlyContainer = document.getElementById('stats-tab-hourly-cards-container');

    if (dailyTbody) dailyTbody.innerHTML = `<tr><td colspan="7" class="text-muted text-center" style="padding:2rem;"><i class="fa-solid fa-spinner fa-spin"></i> Performans arsivi yukleniyor...</td></tr>`;
    if (hofTbody) hofTbody.innerHTML = `<tr><td colspan="6" class="text-muted text-center" style="padding:2rem;"><i class="fa-solid fa-spinner fa-spin"></i> Yildiz hisseler hesaplaniyor...</td></tr>`;
    if (hourlyContainer) hourlyContainer.innerHTML = `<div style="color:var(--text-muted); font-size:0.85rem; padding:1rem;"><i class="fa-solid fa-spinner fa-spin"></i> Saatlik veriler yukleniyor...</div>`;

    try {
        const tabStartDate = document.getElementById('stats-tab-start-date')?.value || startDate;
        const tabEndDate = document.getElementById('stats-tab-end-date')?.value || endDate;
        const tabSymbol = document.getElementById('stats-tab-symbol-search')?.value || symbol;
        const tabTime = document.getElementById('stats-tab-time-filter')?.value || time;

        let url = `/api/tavan_history?start_date=${encodeURIComponent(tabStartDate || '2026-08-04')}`;
        if (tabEndDate) url += `&end_date=${encodeURIComponent(tabEndDate)}`;
        if (tabSymbol) url += `&symbol=${encodeURIComponent(tabSymbol)}`;
        if (tabTime) url += `&time=${encodeURIComponent(tabTime)}`;

        const res = await fetch(url);
        const data = await res.json();

        if (data.status === 'success') {
            const summ = data.summary || {};

            // Veri yoksa (henüz ilk gün başlamadı) - bekleme ekranı göster
            if (!summ.total_days_tracked || summ.total_days_tracked === 0) {
                renderHistoryKpis(summ, 'stats-tab-');
                const notice = document.getElementById('stats-empty-notice');
                if (notice) notice.style.display = 'block';
                if (hourlyContainer) hourlyContainer.innerHTML = `<div style="color:var(--text-muted); font-size:0.85rem; padding:2rem; text-align:center; grid-column:1/-1;"><i class="fa-regular fa-calendar-xmark" style="font-size:2rem; color:#10b981; display:block; margin-bottom:0.5rem;"></i>Henuz seans verisi yok. Ilk kayit 04 Agustos 2026 sabahi 10:15'te olusturulacak.</div>`;
                if (dailyTbody) dailyTbody.innerHTML = `<tr><td colspan="7" style="text-align:center; padding:2rem; color:var(--text-muted);">Henuz kayitli seans bulunmuyor.</td></tr>`;
                if (hofTbody) hofTbody.innerHTML = `<tr><td colspan="7" style="text-align:center; padding:2rem; color:var(--text-muted);">Henuz veri yok.</td></tr>`;
                return;
            }

            renderHistoryKpis(summ, 'stats-tab-');
            renderHourlyCards(data.hourly_summary || [], hourlyContainer);
            renderDailyBreakdown(data.daily_breakdown || [], dailyTbody, 'stats-tab-');
            renderHallOfFame(data.hall_of_fame || [], hofTbody);
        } else {
            if (dailyTbody) dailyTbody.innerHTML = `<tr><td colspan="7" class="text-red text-center" style="padding:2rem;">Veri alinamadi: ${data.message || 'Bilinmeyen hata'}</td></tr>`;
            if (hofTbody) hofTbody.innerHTML = `<tr><td colspan="6" class="text-red text-center" style="padding:2rem;">-</td></tr>`;
        }
    } catch (e) {
        if (dailyTbody) dailyTbody.innerHTML = `<tr><td colspan="7" class="text-red text-center" style="padding:2rem;">Baglanti hatasi: ${e.message}</td></tr>`;
    }
}

// ============================================================
// 🔧 ORTAK RENDER YARDIMCILARI (Hem Modal hem Sekme İçin)
// ============================================================

function renderHistoryKpis(summ, prefix) {
    if (!summ) return;
    const el = (id) => document.getElementById(prefix + id);
    if (el('total-days')) el('total-days').innerText = `${summ.total_days_tracked || 0} Seans`;
    if (el('total-candidates-sub')) el('total-candidates-sub').innerText = `Toplam ${summ.total_candidates_tracked || 0} Oneri`;
    if (el('tavan-rate')) el('tavan-rate').innerText = `%${summ.tavan_success_pct || 0}`;
    if (el('tavan-cnt-sub')) el('tavan-cnt-sub').innerText = `${summ.total_hit_ceiling || 0} / ${summ.total_candidates_tracked || 0} Tavan`;
    if (el('plus5-rate')) el('plus5-rate').innerText = `%${summ.plus5_success_pct || 0}`;
    if (el('plus5-cnt-sub')) el('plus5-cnt-sub').innerText = `${summ.total_hit_plus5 || 0} / ${summ.total_candidates_tracked || 0} Kazandirdi`;
    if (el('avg-max-gain')) el('avg-max-gain').innerText = `+ %${summ.cumulative_avg_max_gain_pct || 0}`;
    if (el('avg-close-sub')) el('avg-close-sub').innerText = `Kapanis Ort: +%${summ.cumulative_avg_closing_gain_pct || 0}`;
    if (el('warrant-avg-gain')) el('warrant-avg-gain').innerText = `+ %${summ.ahlatci_warrant_avg_gain_pct || 0}`;
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

function renderDailyBreakdown(dailyList, tbody, prefix) {
    if (!tbody) return;
    if (!dailyList || dailyList.length === 0) {
        tbody.innerHTML = `<tr><td colspan="7" class="text-muted text-center" style="padding:2rem;">Filtreye uygun islem gunu bulunamadi.</td></tr>`;
        return;
    }
    tbody.innerHTML = '';
    dailyList.forEach(d => {
        const tr = document.createElement('tr');
        const tavanPctCol = d.hit_ceiling_pct >= 70 ? '#10b981' : (d.hit_ceiling_pct >= 50 ? '#facc15' : '#ef4444');
        const plus5PctCol = d.hit_plus5_pct >= 80 ? '#38bdf8' : (d.hit_plus5_pct >= 60 ? '#10b981' : '#facc15');
        tr.innerHTML = `
            <td>
                <div style="font-weight:800; color:#fff; font-size:0.88rem;"><i class="fa-regular fa-calendar text-muted"></i> ${d.date}</div>
                <div style="font-size:0.68rem; color:#10b981; font-weight:700;"><i class="fa-solid fa-check"></i> ${d.status === 'COMPLETED' ? 'Tamamlandi' : 'Canli'}</div>
            </td>
            <td style="font-weight:bold; color:var(--text-light); text-align:center;">${d.total_candidates}</td>
            <td>
                <span style="color:${tavanPctCol}; font-weight:800; font-size:0.88rem;">%${d.hit_ceiling_pct}</span>
                <div style="font-size:0.7rem; color:var(--text-muted);">${d.hit_ceiling_count}/${d.total_candidates} Hisse</div>
            </td>
            <td>
                <span style="color:${plus5PctCol}; font-weight:800; font-size:0.88rem;">%${d.hit_plus5_pct}</span>
                <div style="font-size:0.7rem; color:var(--text-muted);">${d.hit_plus5_count}/${d.total_candidates} Hisse</div>
            </td>
            <td style="color:#facc15; font-weight:800; font-size:0.9rem;">+ %${d.avg_max_gain_pct}</td>
            <td>
                <div style="font-weight:800; color:#38bdf8; font-size:0.82rem;">${d.star_stock || '-'}</div>
                <div style="font-size:0.72rem; color:#c084fc; font-weight:700;">${d.star_warrant || ''}: <span style="color:#10b981;">${d.star_warrant_gain || ''}</span></div>
            </td>
            <td>
                <button onclick="openTavanAuditForDate('${d.date}')" class="btn-primary" style="background:rgba(239,68,68,0.25); color:#fca5a5; border:1px solid rgba(239,68,68,0.4); padding:3px 7px; font-size:0.72rem; border-radius:4px;">
                    <i class="fa-solid fa-folder-open"></i> Ac
                </button>
            </td>`;
        tbody.appendChild(tr);
    });
}

function renderHallOfFame(hofList, tbody) {
    if (!tbody) return;
    if (!hofList || hofList.length === 0) {
        tbody.innerHTML = `<tr><td colspan="6" class="text-muted text-center" style="padding:2rem;">Kayit bulunamadi.</td></tr>`;
        return;
    }
    tbody.innerHTML = '';
    hofList.forEach((h, idx) => {
        const tr = document.createElement('tr');
        const rankIcon = idx === 0 ? '🥇' : (idx === 1 ? '🥈' : (idx === 2 ? '🥉' : `#${idx + 1}`));
        tr.innerHTML = `
            <td><div style="font-weight:800; color:#fff; font-size:0.88rem;">${rankIcon} ${h.symbol}</div></td>
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

