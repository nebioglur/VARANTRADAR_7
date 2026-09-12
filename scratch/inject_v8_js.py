import os

with open('ui/app.js', 'r', encoding='utf-8') as f:
    text = f.read()

v8_js = """
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
                tbody.innerHTML = '<tr><td colspan="4" style="text-align:center; padding:1rem; color:var(--text-muted);">Şu an sıkışma hazırlığında olan hisse yok.</td></tr>';
                return;
            }

            json.data.slice(0, 15).forEach(d => {
                const tr = document.createElement('tr');
                let stateStyle = "color:var(--text-muted)";
                if (d.state === "READY") stateStyle = "color:var(--accent-blue); font-weight:bold;";
                if (d.state === "PREPARING") stateStyle = "color:var(--accent-green);";
                
                tr.innerHTML = `
                    <td style="font-weight:bold; color:var(--text-light);">${d.symbol}</td>
                    <td><span style="${stateStyle}">${d.state}</span></td>
                    <td style="text-align:center;">${d.preparation_score}</td>
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
                tbody.innerHTML = '<tr><td colspan="4" style="text-align:center; padding:1rem; color:var(--text-muted);">Aktif bir kırılım tespit edilmedi.</td></tr>';
                return;
            }

            json.data.slice(0, 15).forEach(d => {
                const tr = document.createElement('tr');
                const fakeRiskColor = d.fakeout_risk > 50 ? "var(--accent-red)" : "var(--accent-green)";
                
                let entryStyle = "color:var(--text-muted);";
                if(d.entry_status === "ENTER") entryStyle = "color:var(--accent-green); font-weight:bold; background:rgba(16,185,129,0.1); padding:2px 6px; border-radius:4px;";
                if(d.entry_status === "WAIT_PULLBACK") entryStyle = "color:var(--accent-yellow);";
                if(d.entry_status === "CHASE_RISK" || d.entry_status === "NO_ENTRY") entryStyle = "color:var(--accent-red);";
                
                tr.innerHTML = `
                    <td style="font-weight:bold; color:var(--accent-green);">${d.symbol}</td>
                    <td style="font-size:0.85rem;">
                        <div style="color:var(--accent-blue)">Güç: ${d.breakout_score}</div>
                        <div style="color:${fakeRiskColor}">Tuzak: %${d.fakeout_risk}</div>
                    </td>
                    <td><span style="${entryStyle}">${d.entry_status}</span></td>
                    <td style="font-size:0.8rem; color:var(--text-muted); max-width:200px; white-space:normal;">${d.entry_reasons[0] || '-'}</td>
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
                tbody.innerHTML = '<tr><td colspan="10" style="text-align:center; padding:1rem; color:var(--text-muted);">Henüz V8 tarafından alınan bir pozisyon kaydı yok.</td></tr>';
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
                    <td style="text-align:right; font-size:0.85rem;">${formatV8Price(d.entry_price, d.t_5m_price)}</td>
                    <td style="text-align:right; font-size:0.85rem;">${formatV8Price(d.entry_price, d.t_15m_price)}</td>
                    <td style="text-align:right; font-size:0.85rem;">${formatV8Price(d.entry_price, d.t_30m_price)}</td>
                    <td style="text-align:right; font-size:0.85rem;">${formatV8Price(d.entry_price, d.t_60m_price)}</td>
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
"""

if 'V8 ENGINE INTEGRATION' not in text:
    with open('ui/app.js', 'a', encoding='utf-8') as f:
        f.write("\n" + v8_js)
    print('Injected V8 JS logic into app.js')
else:
    print('Already injected')
