import urllib.request, json, http.cookiejar

# PythonAnywhere API'yi test et
url = 'https://varantradarpro.pythonanywhere.com/api/simulation/daily_pnl?t=12345'
req = urllib.request.Request(url)
req.add_header('User-Agent', 'Mozilla/5.0')

try:
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode('utf-8'))
        print("STATUS:", data.get('status'))
        trades = data.get('trades', [])
        print(f"TRADES COUNT: {len(trades)}")
        for t in trades:
            print("TRADE:", {k: v for k, v in t.items() if k in ['symbol','entry_price','exit_price','pnl_val','pnl_pct','entry_time','exit_time','shares']})
        
        eq = data.get('equity_curve', [])
        print(f"\nEQUITY_CURVE COUNT: {len(eq)}")
        for e in eq:
            print("  EQ:", e)
        
        ws = data.get('weekly_summary', {})
        print(f"\nWEEKLY_SUMMARY: {ws}")
        
        # Check cumulative_summary key
        cs = data.get('cumulative_summary')
        print(f"\nCUMULATIVE_SUMMARY present: {cs is not None}")
        
        # Check all top-level keys
        print("\nTOP-LEVEL KEYS:", list(data.keys()))
except Exception as e:
    print("ERROR:", e)
