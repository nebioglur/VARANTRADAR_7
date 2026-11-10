import sqlite3
import json

with open('scratch/verd_daily_pnl.json', encoding='utf-8') as f:
    verd_pnl = json.load(f)

conn = sqlite3.connect('data/trading_engine.db')
c = conn.cursor()

# 1. Update trades table
c.execute("DELETE FROM trades WHERE owner='local:nebioglur'")
for t in verd_pnl.get('trades', []):
    cols = [
        'owner', 'date_str', 'symbol', 'entry_time', 'entry_price',
        'exit_time', 'exit_price', 'shares', 'pnl_val', 'pnl_pct',
        'exit_reason', 'strategy_name', 'entry_score', 'entry_checks',
        'atr_value', 'risk_amount', 'market_regime', 'engine_version', 'realized_pnl'
    ]
    vals = [t.get(col) for col in cols]
    placeholders = ','.join(['?'] * len(cols))
    sql = f"INSERT INTO trades ({','.join(cols)}) VALUES ({placeholders})"
    c.execute(sql, vals)

# Also ensure any trades with NULL or empty owner match
c.execute("DELETE FROM trades WHERE owner IS NULL OR owner=''")

# 2. Update equity_log table
c.execute("DELETE FROM equity_log WHERE owner='local:nebioglur'")
for eq in verd_pnl.get('equity_curve', []):
    cols = ['owner', 'date_str', 'start_equity', 'end_equity', 'daily_pnl', 'total_trades', 'win_trades']
    vals = [eq.get(col) for col in cols]
    placeholders = ','.join(['?'] * len(cols))
    sql = f"INSERT INTO equity_log ({','.join(cols)}) VALUES ({placeholders})"
    c.execute(sql, vals)

conn.commit()
conn.close()
print("SUCCESS: Updated data/trading_engine.db to match Verdent daily_pnl")
