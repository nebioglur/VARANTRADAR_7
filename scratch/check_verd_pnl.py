import json

with open('scratch/verd_daily_pnl.json', encoding='utf-8') as f:
    verd_pnl = json.load(f)

print("Status:", verd_pnl.get('status'))
print("Trades count:", len(verd_pnl.get('trades', [])))
for t in verd_pnl.get('trades', []):
    safe_exit = str(t.get('exit_reason', '')).encode('ascii', 'replace').decode('ascii')
    print(f"Trade: {t.get('symbol')} | date: {t.get('date_str')} | pnl: {t.get('pnl_val')} | pnl_pct: {t.get('pnl_pct')}% | exit: {safe_exit}")

print("\nEquity curve:")
for eq in verd_pnl.get('equity_curve', []):
    print(f"Date: {eq.get('date_str')} | Start: {eq.get('start_equity')} | End: {eq.get('end_equity')} | Daily PnL: {eq.get('daily_pnl')}")

print("\nWeekly summary:", verd_pnl.get('weekly_summary'))
print("\nCumulative summary:", verd_pnl.get('cumulative_summary'))
