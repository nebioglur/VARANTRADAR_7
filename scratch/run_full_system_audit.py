import urllib.request, json, time

BASE_URL = "https://varantradarpro.pythonanywhere.com"

opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor())

print("=== 1. AUTHENTICATION & LOGIN ===")
login_req = urllib.request.Request(
    f"{BASE_URL}/login",
    data=b"username=nebioglur&password=123",
    headers={"Content-Type": "application/x-www-form-urlencoded", "User-Agent": "AuditBot/1.0"}
)
with opener.open(login_req, timeout=15) as r:
    print(f"Login Status: {r.status}")
    assert r.status == 200, "Login failed!"

print("\n=== 2. DASHBOARD INIT & MARKET STATUS ===")
dash_req = urllib.request.Request(f"{BASE_URL}/api/dashboard_init?t={int(time.time()*1000)}", headers={"User-Agent": "AuditBot/1.0"})
with opener.open(dash_req, timeout=15) as r:
    d = json.loads(r.read().decode('utf-8'))
    market = d.get('market', {})
    print(f"Market Status: {market.get('label')} (is_open: {market.get('is_open')})")
    print(f"Local Time: {market.get('local_time')}")
    print(f"data_fresh: {d.get('data_fresh')}")
    print(f"stale_data_suppressed: {d.get('stale_data_suppressed')}")
    print(f"last_updated: {d.get('last_updated')}")
    print(f"total_analyzed: {d.get('total_analyzed')}")
    dash_data = d.get('dashboard_data', {})
    all_syms = dash_data.get('all_symbols_stats', {})
    print(f"All Symbols Stats Count: {len(all_syms)}")
    tavan = dash_data.get('tavan_adaylari', [])
    print(f"Tavan Adaylari Count: {len(tavan)}")

print("\n=== 3. V8 ENGINE ENDPOINTS ===")
# V8 Market Regime
with opener.open(urllib.request.Request(f"{BASE_URL}/api/v8/market/regime", headers={"User-Agent": "AuditBot/1.0"}), timeout=15) as r:
    v8_reg = json.loads(r.read().decode('utf-8'))
    print(f"V8 Regime Status: {v8_reg.get('status')}")
    reg = v8_reg.get('regime', {})
    print(f"  Regime Label: {reg.get('label')}, Score: {reg.get('regime_score')}, BIST100 Chg: {reg.get('bist100_chg')}%")

# V8 Playbook
with opener.open(urllib.request.Request(f"{BASE_URL}/api/v8/playbook", headers={"User-Agent": "AuditBot/1.0"}), timeout=15) as r:
    v8_pb = json.loads(r.read().decode('utf-8'))
    print(f"V8 Playbook Status: {v8_pb.get('status')}")
    sc = v8_pb.get('scenario', {})
    print(f"  Scenario: {sc.get('icon')} {sc.get('label')}, Risk: %{sc.get('risk_pct')}, Max Pos: {sc.get('max_positions')}")
    sectors = v8_pb.get('sector_pulse', [])
    print(f"  Sector Pulse Count: {len(sectors)} sectors")
    if sectors:
        top_sec = sectors[:3]
        print(f"  Top Sectors: {', '.join([s.get('sector') + ' (' + str(s.get('avg_change')) + '%)' for s in top_sec])}")

# V8 Weekly Target
with opener.open(urllib.request.Request(f"{BASE_URL}/api/v8/weekly", headers={"User-Agent": "AuditBot/1.0"}), timeout=15) as r:
    v8_wk = json.loads(r.read().decode('utf-8'))
    print(f"V8 Weekly Status: {v8_wk.get('status')}")
    wk = v8_wk.get('weekly', {})
    print(f"  Target: %{wk.get('target_pct')}, Realized: %{wk.get('realized_pct')}, Win Rate: %{wk.get('win_rate_pct')}")

# V8 Discovery
with opener.open(urllib.request.Request(f"{BASE_URL}/api/v8/radar/discovery", headers={"User-Agent": "AuditBot/1.0"}), timeout=15) as r:
    v8_disc = json.loads(r.read().decode('utf-8'))
    print(f"V8 Discovery Status: {v8_disc.get('status')}")
    cands = v8_disc.get('candidates', [])
    print(f"  Discovery Candidates Count: {len(cands)}")

print("\n=== 4. SIMULATION ENDPOINTS ===")
with opener.open(urllib.request.Request(f"{BASE_URL}/api/simulation/summary", headers={"User-Agent": "AuditBot/1.0"}), timeout=15) as r:
    sim_summ = json.loads(r.read().decode('utf-8'))
    print(f"Simulation Summary Status: {sim_summ.get('status')}")
    s = sim_summ.get('summary', {})
    print(f"  Initial Balance: {s.get('initial_balance')} TL")
    print(f"  Current Balance: {s.get('current_balance')} TL")
    print(f"  Total Trades: {s.get('total_trades')}")
    print(f"  Win Rate: {s.get('win_rate')}%")

with opener.open(urllib.request.Request(f"{BASE_URL}/api/simulation/trades?limit=10", headers={"User-Agent": "AuditBot/1.0"}), timeout=15) as r:
    sim_trades = json.loads(r.read().decode('utf-8'))
    print(f"Simulation Trades Status: {sim_trades.get('status')}")
    trades = sim_trades.get('trades', [])
    print(f"  Recent Trades Count: {len(trades)}")
    for t in trades[:3]:
        print(f"    - {t.get('symbol')}: Buy {t.get('buy_price')} -> Sell {t.get('sell_price')} ({t.get('pnl_pct')}%) | {t.get('exit_reason')}")

print("\n=== 5. BACKTEST RUNNER ===")
with opener.open(urllib.request.Request(f"{BASE_URL}/api/backtest/run?symbol=THYAO&stop_pct=1.5&trail_stop_pct=3.0", headers={"User-Agent": "AuditBot/1.0"}), timeout=30) as r:
    bt = json.loads(r.read().decode('utf-8'))
    print(f"Backtest Status: {bt.get('status')}")
    if bt.get('status') == 'success':
        print(f"  Symbol: {bt.get('symbol')}, Total Trades: {bt.get('total_trades')}, Total Return: %{bt.get('total_return_pct')}")

print("\n=== 6. APK DOWNLOAD SERVING ===")
apk_req = urllib.request.Request(f"{BASE_URL}/apk/VarantRadarPro.apk", headers={"User-Agent": "AuditBot/1.0"})
with urllib.request.urlopen(apk_req, timeout=15) as r:
    apk_len = len(r.read())
    print(f"APK Status: {r.status}, Size: {apk_len} bytes, Content-Type: {r.headers.get('Content-Type')}")

print("\n=== ALL BACKEND CHECKS COMPLETED SUCCESSFULLY ===")
