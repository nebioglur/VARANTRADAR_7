import sys, os
sys.path.insert(0, os.path.abspath("."))
import sqlite3, json
from services.trade_database import get_connection

def test_daily_pnl(owner="test_owner"):
    try:
        with get_connection() as conn:
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute("SELECT * FROM equity_log WHERE owner=? ORDER BY date_str ASC", (owner,))
            equity_rows = c.fetchall()
            equity_curve = [dict(row) for row in equity_rows]
            if not equity_curve:
                equity_curve = [{"date_str": "2026-11-05", "start_equity": 100000.0, "end_equity": 100000.0, "total_pnl": 0.0}]

            c.execute("SELECT * FROM trades WHERE owner=? ORDER BY date_str DESC, entry_time DESC", (owner,))
            trade_rows = c.fetchall()
            trades = [dict(row) for row in trade_rows]
            if not trades:
                c.execute("SELECT * FROM trades ORDER BY date_str DESC, entry_time DESC LIMIT 500")
                trade_rows = c.fetchall()
                if trade_rows:
                    trades = [dict(row) for row in trade_rows]
                if not equity_curve or (len(equity_curve) == 1 and float(equity_curve[0].get("daily_pnl") or equity_curve[0].get("total_pnl") or 0.0) == 0.0):
                    c.execute("SELECT * FROM equity_log ORDER BY date_str ASC")
                    eq_fb = c.fetchall()
                    if eq_fb:
                        equity_curve = [dict(row) for row in eq_fb]

            realized_by_date = {}
            for trade in trades:
                trade_date = str(trade.get("date_str") or "")
                if not trade_date:
                    continue
                bucket = realized_by_date.setdefault(trade_date, {"pnl": 0.0, "count": 0, "wins": 0})
                bucket["count"] += 1
                realized = float(trade.get("realized_pnl") or 0)
                bucket["pnl"] += realized
                if trade.get("exit_time") and realized > 0:
                    bucket["wins"] += 1
            if not equity_rows:
                if realized_by_date:
                    equity_curve = []
                    running_balance = 100000.0
                    for trade_date in sorted(realized_by_date):
                        totals = realized_by_date[trade_date]
                        start = running_balance
                        running_balance += totals["pnl"]
                        equity_curve.append({
                            "date_str": trade_date,
                            "start_equity": start,
                            "end_equity": running_balance,
                            "daily_pnl": totals["pnl"],
                            "total_trades": totals["count"],
                            "win_trades": totals["wins"],
                        })
            else:
                known_dates = {str(row.get("date_str") or "") for row in equity_curve}
                for trade_date in realized_by_date:
                    if trade_date not in known_dates:
                        equity_curve.append({"date_str": trade_date, "start_equity": 100000.0, "end_equity": 100000.0, "daily_pnl": 0.0})
                equity_curve.sort(key=lambda row: str(row.get("date_str") or ""))
            previous_end = None
            for row in equity_curve:
                day = str(row.get("date_str") or "")
                start = previous_end if previous_end is not None else float(row.get("start_equity") or 100000.0)
                totals = realized_by_date.get(day)
                if totals is not None:
                    daily_pnl = totals["pnl"]
                    row["total_trades"] = totals["count"]
                    row["win_trades"] = totals["wins"]
                else:
                    daily_pnl = float(row.get("daily_pnl") or 0)
                row["start_equity"] = start
                row["daily_pnl"] = daily_pnl
                row["end_equity"] = start + daily_pnl
                previous_end = row["end_equity"]
            
            c.execute("SELECT COUNT(*), COALESCE(SUM(pnl_val), 0.0), SUM(CASE WHEN pnl_val > 0 THEN 1 ELSE 0 END) FROM trades WHERE owner=? AND exit_time IS NOT NULL", (owner,))
            tot_row = c.fetchone()
            print("tot_row:", tot_row)
            
            c.execute("SELECT COALESCE(SUM(pnl_val), 0.0), COUNT(*) FROM live_positions WHERE owner=? AND pnl_val IS NOT NULL", (owner,))
            lp_row = c.fetchone()
            print("lp_row:", lp_row)

            from services.statistics_engine import StatisticsEngine
            perf = StatisticsEngine.get_trade_performance(owner)
            print("perf:", perf)
            print("SUCCESS!")
    except Exception as e:
        import traceback
        traceback.print_exc()

test_daily_pnl()
