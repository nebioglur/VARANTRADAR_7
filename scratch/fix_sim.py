import re

with open('server.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix backtest/run
content = re.sub(
    r'"backtest": bt_results,\s*"monte_carlo": mc_results',
    r'"backtest": sanitize_for_json(bt_results),\n        "monte_carlo": sanitize_for_json(mc_results)',
    content
)

# Fix simulation/live_orders
content = re.sub(
    r'"orders": sorted\(orders, key=lambda x: x\[\'score\'\], reverse=True\)',
    r'"orders": sanitize_for_json(sorted(orders, key=lambda x: x[\'score\'], reverse=True))',
    content
)

# Fix simulation/daily_pnl
content = re.sub(
    r'"equity_curve": equity_curve,\s*"trades": trades',
    r'"equity_curve": sanitize_for_json(equity_curve),\n        "trades": sanitize_for_json(trades)',
    content
)

with open('server.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("Sanitized Backtest and Simulation APIs!")
