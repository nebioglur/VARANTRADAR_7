import sys, os, json
sys.path.insert(0, os.getcwd())

from services.market_data import MarketDataManager
from services.simulation_engine import SimulationEngine
from services.trade_database import get_connection

with open('dashboard_cache.json', 'r', encoding='utf-8') as f:
    cache = json.load(f)

daily_stats = cache.get("all_symbols_stats", {})
tavan_candidates = cache.get("tavan_adaylari", [])

all_sim_cands = list(tavan_candidates or [])
sim_seen = {c.get('symbol') or c.get('Symbol') for c in all_sim_cands if (c.get('symbol') or c.get('Symbol'))}
for opp in (cache.get('opportunities_1h', []) + cache.get('opportunities', [])):
    osym = opp.get('symbol') or opp.get('Symbol')
    if osym and osym not in sim_seen:
        all_sim_cands.append(opp)
        sim_seen.add(osym)

for sym, d in (daily_stats or {}).items():
    if not isinstance(d, dict) or sym in sim_seen:
        continue
    price = float(d.get('Price') or d.get('Daily_Close') or 0)
    ch = float(d.get('Change_Pct') or 0)
    vol = float(d.get('Vol_Multiplier') or d.get('Volume_Ratio') or 0)
    vol_tl = float(d.get('Volume_TL') or (float(d.get('Volume', 0)) * price) or 0)
    if price >= 4.0 and 0.5 <= ch < 5.2 and vol >= 1.2 and vol_tl >= 25_000_000:
        cand = dict(d)
        cand['symbol'] = sym
        cand['score'] = float(d.get('Score') or 92.0)
        cand['morning_price'] = price
        cand['ceiling_target'] = price * 1.10
        cand['morning_phase'] = 'Phase 1 (10:15)'
        all_sim_cands.append(cand)
        sim_seen.add(sym)

print(f"Total candidates prepared: {len(all_sim_cands)}")
d_str = "2026-11-05"
MarketDataManager.record_signals(d_str, all_sim_cands)

# Fetch intraday for top 10
conn = get_connection()
cur = conn.cursor()
cur.execute("SELECT symbol FROM signals WHERE date_str = ? ORDER BY score DESC LIMIT 10", (d_str,))
top_syms = [r["symbol"] for r in cur.fetchall()]
conn.close()
print(f"Top 10 symbols to fetch intraday for: {top_syms}")

# Fetch intraday
import yfinance as yf, pandas as pd
insert_sql = """
INSERT INTO market_data (date_str, timestamp, symbol, open, high, low, close, volume, interval, source)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, '5m', 'yfinance')
ON CONFLICT(timestamp, symbol) DO NOTHING
"""
all_rows = []
for sym in top_syms:
    try:
        data = yf.download([sym], period="5d", interval="5m", group_by='ticker', progress=False)
        if data is None or data.empty: continue
        if isinstance(data.columns, pd.MultiIndex):
            if sym in data.columns.get_level_values(0):
                df = data[sym]
            else:
                df = data
        else:
            df = data
        df = df.dropna(how='all')
        for idx_time, row in df.iterrows():
            ts = pd.Timestamp(idx_time)
            if ts.tzinfo is None:
                ts = ts.tz_localize("Europe/Istanbul")
            else:
                ts = ts.tz_convert("Europe/Istanbul")
            if ts.strftime("%Y-%m-%d") != d_str: continue
            _o, _h, _l, _c, _v = float(row['Open']), float(row['High']), float(row['Low']), float(row['Close']), float(row['Volume'])
            all_rows.append((d_str, ts.isoformat(), sym, _o, _h, _l, _c, _v))
    except Exception as e:
        print(f"Error {sym}: {e}")

conn = get_connection()
cur = conn.cursor()
if all_rows:
    cur.executemany(insert_sql, all_rows)
    conn.commit()
print(f"Inserted {len(all_rows)} market data bars.")
conn.close()

# Now run simulation
print("\n--- Running SimulationEngine ---")
sim = SimulationEngine(owner="local:nebioglur")
sim.run_daily_simulation(d_str)

# Check trades recorded
conn = get_connection()
cur = conn.cursor()
cur.execute("SELECT symbol, entry_time, entry_price, exit_time, exit_price, pnl_val, pnl_pct, exit_reason FROM trades WHERE date_str = ?", (d_str,))
trades = cur.fetchall()
print(f"\nTotal trades recorded in trades table for {d_str}: {len(trades)}")
for t in trades:
    print("  Trade:", t)
conn.close()
