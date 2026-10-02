import re

# 1. Update telegram_bot.py
with open("services/telegram_bot.py", "r", encoding="utf-8") as f:
    t_text = f.read()

pattern_tg = r'def notify_sim_trade\(symbol.*?return send_telegram_message\(text\)'
replacement_tg = """def notify_sim_trade(symbol: str, action: str, price: float, pnl_pct: float = 0.0, reason: str = "", date_str: str = "", trade: dict = None) -> bool:
    import json, os
    from datetime import datetime
    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")
        
    cache_file = "data/sent_sim_alerts.json"
    cache = {}
    if os.path.exists(cache_file):
        try:
            with open(cache_file, "r", encoding="utf-8") as f_c:
                cache = json.load(f_c)
        except:
            pass
            
    if cache.get("date") != date_str:
        cache = {"date": date_str, "alerts": []}
        
    alert_key = f"{symbol}_{action}_{price:.2f}"
    if alert_key in cache["alerts"]:
        return True
        
    cache["alerts"].append(alert_key)
    try:
        with open(cache_file, "w", encoding="utf-8") as f_c:
            json.dump(cache, f_c)
    except:
        pass
        
    trade = trade or {}
    shares = trade.get('shares', 0)
    total_val = shares * price if shares else 0
    tp1 = trade.get('tp1_price', 0)
    sl = trade.get('stop_price', 0)
    entry = trade.get('entry_price', price)
    
    tp_pct = ((tp1 - entry) / entry * 100) if tp1 and entry else 0
    sl_pct = ((entry - sl) / entry * 100) if sl and entry else 0
    
    if "AL" in action:
        text = (f"\U0001F916 <b>SIMULASYON {action}</b>\\n\\n"
                f"\U0001F4C8 <b>{symbol}</b> -> {price:.2f} TL\\n"
                f"\U0001F4E6 <b>Lot Sayisi:</b> {shares} Lot\\n"
                f"\U0001F4B0 <b>Toplam Tutar:</b> {total_val:.2f} TL\\n\\n"
                f"\U0001F3AF <b>Kar Al (TP):</b> {tp1:.2f} TL (+%{tp_pct:.1f})\\n"
                f"\U0001F6D1 <b>Stop Sat (SL):</b> {sl:.2f} TL (-%{sl_pct:.1f})\\n")
        if reason:
            text += f"\\n\U0001F4A1 <b>Neden:</b> {reason}"
        return send_telegram_message(text)
    else:
        emoji = "\U0001F7E2" if pnl_pct >= 0 else "\U0001F534"
        pnl_val = trade.get('pnl_val', 0)
        text = (f"\U0001F916 <b>SIMULASYON {action}</b>\\n\\n"
                f"\U0001F4C9 <b>{symbol}</b> -> {price:.2f} TL\\n"
                f"\U0001F4E6 <b>Lot Sayisi:</b> {shares} Lot\\n"
                f"\U0001F4B0 <b>Cikis Tutari:</b> {total_val:.2f} TL\\n\\n"
                f"{emoji} <b>K/Z (Tutar):</b> {pnl_val:+.2f} TL\\n"
                f"{emoji} <b>K/Z (%):</b> %{pnl_pct:+.2f}\\n")
        if reason:
            text += f"\\n\U0001F4A1 <b>Neden:</b> {reason}"
        return send_telegram_message(text)"""

t_text = re.sub(pattern_tg, replacement_tg, t_text, flags=re.DOTALL)

with open("services/telegram_bot.py", "w", encoding="utf-8") as f:
    f.write(t_text)

# 2. Update simulation_engine.py
with open("services/simulation_engine.py", "r", encoding="utf-8") as f:
    s_text = f.read()

s_text = s_text.replace(
    'notify_sim_trade(sym, "AL", entry_price, 0.0, "Sistem AL verdi", str(current_time)[:10])',
    'notify_sim_trade(sym, "AL", entry_price, 0.0, "Sistem AL verdi", str(current_time)[:10], active_trades[-1])'
)

s_text = s_text.replace(
    'notify_sim_trade(sym, "AL (Yeniden)", entry_price, 0.0, "Yeniden Giris", str(current_time)[:10])',
    'notify_sim_trade(sym, "AL (Yeniden)", entry_price, 0.0, "Yeniden Giris", str(current_time)[:10], active_trades[-1])'
)

s_text = s_text.replace(
    'notify_sim_trade(sym, "SAT", sell_price, trade["pnl_pct"], reason, str(current_time)[:10])',
    'notify_sim_trade(sym, "SAT", sell_price, trade["pnl_pct"], reason, str(current_time)[:10], trade)'
)

s_text = s_text.replace(
    'notify_sim_trade(sym, "SAT (GUN SONU)", close, trade["pnl_pct"], "17:50 Otomatik Kapanis", str(last_time)[:10])',
    'notify_sim_trade(sym, "SAT (GUN SONU)", close, trade["pnl_pct"], "17:50 Otomatik Kapanis", str(last_time)[:10], trade)'
)

with open("services/simulation_engine.py", "w", encoding="utf-8") as f:
    f.write(s_text)

print("SIM DETAILS PATCH OK")
