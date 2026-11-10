import sys
import re
sys.stdout.reconfigure(encoding='utf-8')

with open('ui/index.html', 'r', encoding='utf-8', errors='ignore') as f:
    html = f.read()

with open('pro8_app.js', 'r', encoding='utf-8', errors='ignore') as f:
    js = f.read()

# 1. Check all element IDs referenced in pro8_app.js that are expected on Home tab
home_ids = [
    'home-wrapper', 'market-closed-warning', 'market-closed-warning-detail',
    'live-clock', 'live-date', 'total-analyzed-counter', 'last-scan-time',
    'manual-scan-btn', 'manual-scan-panel', 'scan-progress-bar',
    'scan-progress-detail', 'scan-percent-text', 'scan-phase-text',
    'scan-elapsed', 'scan-cancel-btn', 'scan-found-stats',
    'scan-found-tavan', 'scan-found-1h', 'scan-found-5m', 'scan-found-mtf',
    'radar-cards-grid', 'mtf-card', 'mtf-count', 'mtf-loading', 'mtf-table-body',
    'radar-card-99', 'all-stocks-search', 'all-stocks-count', 'tb-all-stocks-home',
    'radar-card-0', 'time-tavan-adaylari', 'tb-tavan-adaylari',
    'radar-card-2', 'arge-last-scan', 'tb-arge-tavan',
    'radar-card-1', 'time-opportunities-1h', 'tb-opportunities-1h',
    'radar-card-3', 'time-opportunities', 'tb-opportunities',
    'radar-card-defensive', 'time-defensive', 'defensive-tbody',
    'time-favorites', 'tb-favorites', 'time-high_volume', 'tb-high_volume',
    'radar-card-4', 'time-gainers', 'tb-gainers',
    'radar-card-5', 'time-losers', 'tb-losers',
    'time-low_volume', 'tb-low_volume',
    'radar-card-stay-away', 'time-stay-away-1h', 'tb-stay-away-1h',
    'dip-breakout-card', 'time-dip-breakout', 'tb-dip-breakout',
    'home-committee-summary', 'home-advice-short', 'home-advice-long', 'home-top-picks',
    'shield-status', 'home-kpi-cumulative-equity'
]

print("Checking presence of Home IDs in index.html:")
missing = []
for hid in home_ids:
    if f'id="{hid}"' not in html and f"id='{hid}'" not in html:
        missing.append(hid)
print("Missing IDs:", missing)

# 2. Check if functions called in onclick handlers exist in pro8_app.js
onclicks = re.findall(r'onclick=["\']([^"\']+)["\']', html)
fn_calls = set()
for oc in onclicks:
    calls = re.findall(r'(\b\w+)\s*\(', oc)
    for c in calls:
        if c not in {'if', 'for', 'switch', 'catch', 'function', 'return', 'typeof', 'alert'}:
            fn_calls.add(c)

print(f"\nChecking {len(fn_calls)} onclick functions in pro8_app.js:")
missing_fns = []
for fn in sorted(fn_calls):
    pattern = rf'\b(?:function\s+{fn}|(?:window\.)?{fn}\s*=\s*(?:async\s+)?function|const\s+{fn}\s*=\s*\(|let\s+{fn}\s*=\s*\()'
    if not re.search(pattern, js):
        missing_fns.append(fn)

print("Functions missing in pro8_app.js:", missing_fns)
