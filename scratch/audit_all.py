import sys, os
sys.path.insert(0, os.getcwd())

print("=== 1. V8 REGIME TEST ===")
try:
    from v8_engine.regime import MarketRegimeEngine
    mre = MarketRegimeEngine()
    print("MarketRegimeEngine init: OK")
except Exception as e:
    print("MarketRegimeEngine ERROR:", e)

print("\n=== 2. V8 PLAYBOOK TEST ===")
try:
    from v8_engine.playbook import get_scenario, get_weekly_guard, evaluate_v8_signal
    sc = get_scenario()
    print("get_scenario: OK, regime =", sc.get("regime"))
    wg = get_weekly_guard(100.0, 100000.0, "BULL")
    print("get_weekly_guard: OK, status =", wg.get("status"))
except Exception as e:
    print("V8 Playbook ERROR:", e)

print("\n=== 3. V8 DATABASE TEST ===")
try:
    from v8_engine.database import V8Database
    V8Database.init_db()
    conn = V8Database.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r[0] for r in cur.fetchall()]
    print("V8 Tables:", tables)
    conn.close()
except Exception as e:
    print("V8 DB ERROR:", e)

print("\n=== 4. TRADE DATABASE TEST ===")
try:
    from services.trade_database import get_connection, init_db
    init_db()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r[0] for r in cur.fetchall()]
    print("Trade DB Tables:", tables)
    conn.close()
except Exception as e:
    print("Trade DB ERROR:", e)

print("\n=== 5. SIMULATION ENGINE TEST ===")
try:
    from services.simulation_engine import SimulationEngine
    sim = SimulationEngine(owner="local:nebioglur")
    print("SimulationEngine init: OK")
except Exception as e:
    print("SimulationEngine ERROR:", e)

print("\n=== 6. STATISTICS ENGINE TEST ===")
try:
    from services.statistics_engine import StatisticsEngine
    perf = StatisticsEngine.get_trade_performance("local:nebioglur")
    print("StatisticsEngine get_trade_performance: OK, total_trades =", perf.get("total_trades"))
except Exception as e:
    print("StatisticsEngine ERROR:", e)

print("\n=== 7. TELEGRAM BOT CREDENTIALS & DEDUP TEST ===")
try:
    from services.telegram_bot import get_telegram_credentials, claim_telegram_alert
    bt, cid = get_telegram_credentials()
    print("Credentials read: token is", "SET" if bt else "EMPTY", "| chat_id is", "SET" if cid else "EMPTY")
    c1 = claim_telegram_alert("TEST_DEDUP_KEY_12345")
    c2 = claim_telegram_alert("TEST_DEDUP_KEY_12345")
    print("Dedup claim first:", c1, "| second (should be False):", c2)
except Exception as e:
    print("Telegram ERROR:", e)

print("\n=== AUDIT COMPLETE ===")
