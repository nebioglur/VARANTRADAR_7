"""Postgres modunda uçtan uca fonksiyon testi (yerel makineden)."""
import os
import sys

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql://postgres.kfslwkmrnjqxirzhfmbn:VR7data_2026_xK9mTq4pLw2n@aws-0-eu-central-1.pooler.supabase.com:6543/postgres",
)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services import trade_database
print("IS_PG:", trade_database.IS_PG)
assert trade_database.IS_PG

from services.live_trade_monitor import (
    open_position, close_position, get_terminal_state, reset_portfolio,
)

OWNER = "local:test_kullanici"

# 1. terminal durumu (yeni owner -> 100000 bakiye)
st = get_terminal_state(owner=OWNER)
print("bakiye:", st.get("cash"))
assert abs(st["cash"] - 100000.0) < 0.01, st
assert len(st.get("open", [])) == 0

# 2. pozisyon ac
res = open_position("THYAO", allocation=10000.0, tp_pct=5.0, sl_pct=3.0, owner=OWNER)
print("open:", res)

st = get_terminal_state(owner=OWNER)
print("bakiye acilis sonrasi:", st.get("cash"), "pozisyon:", len(st.get("open", [])))
assert len(st["open"]) == 1

pid = st["open"][0]["id"]

# 3. pozisyon kapat
res2 = close_position(pid, price=None, reason="TEST", owner=OWNER)
print("close:", res2)
st = get_terminal_state(owner=OWNER)
assert len(st["open"]) == 0

# 4. reset (trades + equity_log temizlenir, bakiye 100k)
reset_portfolio(OWNER)
st = get_terminal_state(owner=OWNER)
assert abs(st["cash"] - 100000.0) < 0.01

# 5. daily pnl sorgusu (owner filtreli)
from services.trade_database import get_connection
with get_connection() as conn:
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM trades WHERE owner = ?", (OWNER,))
    print("trades:", cur.fetchone()[0])
    cur.execute("SELECT COUNT(*) FROM equity_log WHERE owner = ?", (OWNER,))
    print("equity_log:", cur.fetchone()[0])

# 6. V8: save_signal + regime upsert + outcome
from v8_engine.database import V8Database
V8Database.save_signal({
    "signal_id": "PG_TEST_SIGNAL_1",
    "symbol": "THYAO",
    "strategy": "TEST",
    "score": 88.5,
    "market_regime": "NEUTRAL",
})
V8Database.save_signal({  # REPLACE -> upsert testi
    "signal_id": "PG_TEST_SIGNAL_1",
    "symbol": "THYAO",
    "strategy": "TEST",
    "score": 91.0,
})
conn = V8Database.get_connection()
cur = conn.cursor()
cur.execute("SELECT score, strategy FROM v8_signals WHERE signal_id = ?", ("PG_TEST_SIGNAL_1",))
row = cur.fetchone()
print("v8_signal:", dict(row) if row else None)
assert row is not None and abs(row["score"] - 91.0) < 0.001
cur.execute("INSERT OR IGNORE INTO v8_outcomes (signal_id, t_3m_price, final_result) VALUES (?, ?, ?)",
            ("PG_TEST_SIGNAL_1", 101.5, "WIN"))
cur.execute("SELECT t_3m_price, final_result FROM v8_outcomes WHERE signal_id = ?", ("PG_TEST_SIGNAL_1",))
print("v8_outcome:", cur.fetchone()["t_3m_price"])
conn.commit()
conn.close()

# 7. temizlik
with get_connection() as conn:
    cur = conn.cursor()
    cur.execute("DELETE FROM trades WHERE owner = ?", (OWNER,))
    cur.execute("DELETE FROM equity_log WHERE owner = ?", (OWNER,))
    cur.execute("DELETE FROM live_positions WHERE owner = ?", (OWNER,))
    cur.execute("DELETE FROM live_settings WHERE key = ?", ("live_cash:" + OWNER,))
    cur.execute("DELETE FROM v8_signals WHERE signal_id = ?", ("PG_TEST_SIGNAL_1",))
    cur.execute("DELETE FROM v8_outcomes WHERE signal_id = ?", ("PG_TEST_SIGNAL_1",))
print("\nTUM PG TESTLERI GECTI")
