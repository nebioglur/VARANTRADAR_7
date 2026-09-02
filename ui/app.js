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

        renderStatsMode();
            
            // Popüle Et: Daily History Tablosu
            if (dailyTbody) {
                dailyTbody.innerHTML = '';
                if (history.length === 0) {
                    dailyTbody.innerHTML = `<tr><td colspan="6" class="text-muted text-center" style="padding:2rem;">Henüz kaydedilmiş seans bulunmuyor.</td></tr>`;
                } else {
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
            }
        } else {
            if (dailyTbody) dailyTbody.innerHTML = `<tr><td colspan="6" class="text-red text-center" style="padding:2rem;">Veri alınamadı: ${data.message || 'Bilinmeyen hata'}</td></tr>`;
        }
    } catch (e) {
        if (dailyTbody) dailyTbody.innerHTML = `<tr><td colspan="6" class="text-red text-center" style="padding:2rem;">Baglanti hatasi: ${e.message}</td></tr>`;
    }
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
    
    let allItems = global_stats_data.summary?.all_time_symbols || [];
    
    if (type === 'tavan') {
        items = allItems.filter(it => it.hit_ceiling);
        titleText = '<i class="fa-solid fa-rocket"></i> Tüm Zamanların Tavan Hisseleri';
    } else if (type === 'plus5') {
        items = allItems.filter(it => it.hit_plus5);
        titleText = '<i class="fa-solid fa-chart-line"></i> Tüm Zamanların +%5 Yapan Hisseleri';
    } else if (type === 'positive_close') {
        items = allItems.filter(it => it.closing_gain_pct > 0);
        titleText = '<i class="fa-solid fa-arrow-trend-up"></i> Günü Kârda Kapatanlar';
    } else if (type === 'negative_close') {
        items = allItems.filter(it => it.closing_gain_pct < 0);
        titleText = '<i class="fa-solid fa-arrow-trend-down"></i> Günü Zararda Kapatanlar';
    } else if (type === 'elite_positive_close') {
        items = allItems.filter(it => it.closing_gain_pct > 0 && (it.morning_score >= 99.9));
        titleText = '<i class="fa-solid fa-medal text-yellow"></i> Elit Kârda Kapatanlar (100 Puan)';
    } else if (type === 'elite_negative_close') {
        items = allItems.filter(it => it.closing_gain_pct < 0 && (it.morning_score >= 99.9));
        titleText = '<i class="fa-solid fa-medal text-yellow"></i> Elit Zararda Kapatanlar (100 Puan)';
    } else if (type === 'elite_all') {
        items = allItems.filter(it => it.morning_score >= 99.9);
        titleText = '<i class="fa-solid fa-medal text-yellow"></i> Tüm Elit Öneriler (100 Puan)';
    } else if (type === 'all') {
        items = allItems;
        titleText = '<i class="fa-solid fa-list-ul"></i> Sistemin Tüm Önerileri';
    } else if (type === 'daily_all' && date) {
        const dayData = (global_stats_data.daily_breakdown || []).find(d => d.date === date);
        items = dayData?.all_symbols || [];
        titleText = `<i class="fa-regular fa-calendar"></i> ${date} Tarihli Tüm Öneriler`;
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
            
            const cPrice = item.closing_price ? item.closing_price.toFixed(2) : '-';
            const cPct = item.closing_gain_pct !== undefined ? item.closing_gain_pct.toFixed(2) : '-';
            const cColor = item.closing_gain_pct > 0 ? 'var(--accent-green)' : (item.closing_gain_pct < 0 ? 'var(--accent-red)' : 'var(--text-muted)');
            
            const maxG = item.max_gain_pct !== undefined ? item.max_gain_pct.toFixed(2) : (item.max_gain !== undefined ? item.max_gain : '-');

            const hitStatus = item.hit_ceiling ? '<span style="background:rgba(16,185,129,0.2); color:#10b981; padding:2px 5px; border-radius:4px; font-size:0.7rem;">🔥 TAVAN</span>' : (item.hit_plus5 ? '<span style="background:rgba(56,189,248,0.2); color:#38bdf8; padding:2px 5px; border-radius:4px; font-size:0.7rem;">⭐ +%5</span>' : '');

            const card = document.createElement('div');
            card.style.background = 'rgba(255,255,255,0.05)';
            card.style.border = '1px solid rgba(255,255,255,0.1)';
            card.style.borderRadius = '8px';
            card.style.padding = '0.8rem';
            card.style.textAlign = 'center';
            card.style.display = 'flex';
            card.style.flexDirection = 'column';
            card.style.justifyContent = 'space-between';
            card.innerHTML = `
                ${dt}
                <div style="font-weight:900; color:var(--text-main); font-size:1.2rem; margin-bottom:5px;">${sym}</div>
                <div style="display:flex; justify-content:space-between; font-size:0.75rem; margin-bottom:4px; background:rgba(0,0,0,0.2); padding:4px; border-radius:4px;">
                    <span style="color:var(--text-muted);">Öneri:</span>
                    <span><b style="color:#fff;">${mPrice}</b> (<span style="color:${mColor}">${mPct > 0 ? '+' : ''}${mPct}%</span>)</span>
                </div>
                <div style="display:flex; justify-content:space-between; font-size:0.75rem; margin-bottom:4px; background:rgba(0,0,0,0.2); padding:4px; border-radius:4px;">
                    <span style="color:var(--text-muted);">Kapanış:</span>
                    <span><b style="color:#fff;">${cPrice}</b> (<span style="color:${cColor}">${cPct > 0 ? '+' : ''}${cPct}%</span>)</span>
                </div>
                <div style="display:flex; justify-content:space-between; font-size:0.75rem; margin-bottom:8px; background:rgba(0,0,0,0.2); padding:4px; border-radius:4px;">
                    <span style="color:var(--text-muted);">Zirve Kâr:</span>
                    <span style="color:var(--accent-yellow); font-weight:bold;">+${maxG}%</span>
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

async function fetchSimulationData() {
    const tbody = document.getElementById('sim-trade-log-tbody');
    if (tbody) tbody.innerHTML = '<tr><td colspan="6" class="text-muted text-center" style="padding:2rem;"><i class="fa-solid fa-spinner fa-spin"></i> İşlem Geçmişi Yükleniyor...</td></tr>';
    
    try {
        const res = await fetch(`/api/simulation/daily_pnl?t=` + Date.now());
        const data = await res.json();
        
        if (data.status === 'success') {
            globalSimData = data;
            fetchLiveOrders();
            
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
                        const exitPriceStr = isClosed ? `₺${t.exit_price.toFixed(2)}` : '-';
                        const pnlValStr = isClosed ? `${pnlSign}₺${(t.pnl_val || 0).toFixed(2)}` : '-';
                        const pnlPctStr = isClosed ? `${pnlSign}${(t.pnl_pct || 0).toFixed(2)}%` : '-';
                        const statusStr = isClosed ? (t.exit_reason || 'Kapandı') : '<span style="color:var(--accent-yellow); font-weight:bold;"><i class="fa-solid fa-spinner fa-spin"></i> AÇIK POZİSYON</span>';

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

let equityChartInstance = null;

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

