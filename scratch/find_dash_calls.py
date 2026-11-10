import sys
sys.stdout.reconfigure(encoding='utf-8')

for fname in ['ui/app.js', 'pro8_app.js']:
    print(f"\n--- {fname} Dashboard Calls ---")
    with open(fname, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
    for i, l in enumerate(lines):
        if any(w in l for w in ['dashboard_init', 'initDashboard', 'fetchDashboard', 'renderAllDashboardTables(']):
            print(f"L{i+1}: {l.strip()[:100]}")
