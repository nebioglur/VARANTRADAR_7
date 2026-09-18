with open("services/telegram_bot.py", "r", encoding="utf-8") as f:
    text = f.read()

import re
pattern = r'def notify_sim_trade\(symbol: str, action.*?return send_telegram_message\(text\)'

new_func = """def notify_sim_trade(symbol: str, action: str, price: float, pnl_pct: float = 0.0, reason: str = "", date_str: str = "", trade: dict = None) -> bool:
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
        text = "?? <b>SÝMÜLASYON " + action + "</b>\\n\\n"
        text += "?? <b>" + symbol + "</b> ? " + f"{price:.2f}" + " TL\\n"
        text += "?? <b>Lot Sayýsý:</b> " + str(shares) + " Lot\\n"
        text += "?? <b>Toplam Tutar:</b> " + f"{total_val:.2f}" + " TL\\n\\n"
        text += "?? <b>Kâr Al (TP):</b> " + f"{tp1:.2f}" + " TL (+%" + f"{tp_pct:.1f}" + ")\\n"
        text += "?? <b>Stop Sat (SL):</b> " + f"{sl:.2f}" + " TL (-%" + f"{sl_pct:.1f}" + ")\\n"
        if reason:
            text += "\\n?? <b>Neden:</b> " + reason
        return send_telegram_message(text)
    else:
        emoji = "??" if pnl_pct >= 0 else "??"
        pnl_val = trade.get('pnl_val', 0)
        text = "?? <b>SÝMÜLASYON " + action + "</b>\\n\\n"
        text += "?? <b>" + symbol + "</b> ? " + f"{price:.2f}" + " TL\\n"
        text += "?? <b>Lot Sayýsý:</b> " + str(shares) + " Lot\\n"
        text += "?? <b>Çýkýþ Tutarý:</b> " + f"{total_val:.2f}" + " TL\\n\\n"
        text += emoji + " <b>K/Z (Tutar):</b> " + f"{pnl_val:+.2f}" + " TL\\n"
        text += emoji + " <b>K/Z (%):</b> %" + f"{pnl_pct:+.2f}" + "\\n"
        if reason:
            text += "\\n?? <b>Neden:</b> " + reason
        return send_telegram_message(text)"""

text = re.sub(pattern, new_func.replace('\\n', '\n'), text, flags=re.DOTALL)

with open("services/telegram_bot.py", "w", encoding="utf-8") as f:
    f.write(text)
print("FIX OK")
