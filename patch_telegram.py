# -*- coding: utf-8 -*-
with open('services/telegram_bot.py', 'r', encoding='utf-8') as f:
    text = f.read()

new_func = """
def notify_sim_trade(symbol: str, action: str, price: float, pnl_pct: float = 0.0, reason: str = "", date_str: str = "") -> bool:
    import json, os
    from datetime import datetime
    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")
        
    cache_file = "data/sent_sim_alerts.json"
    cache = {}
    if os.path.exists(cache_file):
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                cache = json.load(f)
        except:
            pass
            
    if cache.get("date") != date_str:
        cache = {"date": date_str, "alerts": []}
        
    alert_key = f"{symbol}_{action}_{price:.2f}"
    if alert_key in cache["alerts"]:
        return True # Zaten gonderildi
        
    cache["alerts"].append(alert_key)
    try:
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(cache, f)
    except:
        pass
        
    if "AL" in action:
        text = (f"?? <b>SÝMÜLASYON {action}</b>\\n"
                f"?? {symbol} ? {price:.2f} TL\\n")
        if reason:
            text += f"?? Neden: {reason}"
        return send_telegram_message(text)
    else:
        emoji = "??" if pnl_pct >= 0 else "??"
        text = (f"?? <b>SÝMÜLASYON {action}</b>\\n"
                f"?? {symbol} ? {price:.2f} TL\\n"
                f"{emoji} K/Z: %{pnl_pct:+.2f}\\n")
        if reason:
            text += f"?? Neden: {reason}"
        return send_telegram_message(text)
"""

text += "\n" + new_func

with open('services/telegram_bot.py', 'w', encoding='utf-8') as f:
    f.write(text)
print("TELEGRAM PATCH OK")
