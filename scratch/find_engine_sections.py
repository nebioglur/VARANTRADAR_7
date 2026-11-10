with open('services/simulation_engine.py', 'r', encoding='utf-8') as f:
    text = f.read()

# Check key sections
sections = [
    "_position_allocation",
    "_daily_trend_values",
    "_run_daily_simulation_inner",
    "valid_signals.sort",
    "for current_time in sorted_times:",
    "if low <= stop_price:",
    "elif high >= tp1_price",
    "# 2. YEN? ALIMLARI KONTROL ET",
    "close_open_now"
]
for s in sections:
    pos = text.find(s)
    print(f"Section '{s}': found at index {pos}")
