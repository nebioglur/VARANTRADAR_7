# -*- coding: utf-8 -*-
with open('services/notification_manager.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Hatalı olan 297 ile 315. satırlar arasını silip temiz kod ekleyeceğiz.
# Ama tam olarak nerede başladığını bulalım.
start_idx = -1
end_idx = -1
for i, line in enumerate(lines):
    if "def send_simulation_trade_alert" in line:
        start_idx = i
    if "def send_portfolio_alert" in line:
        end_idx = i + 2 # return False dahil

new_code = '''    def send_simulation_trade_alert(self, symbol: str, action: str, price: float, time_str: str, pnl_pct: float = None, reason: str = "") -> bool:
        import json, os
        from datetime import datetime
        cache_file = "data/sent_sim_trades.json"
        today = datetime.now().strftime("%Y-%m-%d")
        uid = f"{today}_{symbol}_{action}_{time_str}"
        sent_trades = []
        if os.path.exists(cache_file):
            try:
                with open(cache_file, "r") as f: sent_trades = json.load(f)
            except: pass
        if uid in sent_trades: return False
        
        icon = "GREEN" if action.startswith("AL") else "RED"
        clean_sym = symbol.replace(".IS", "").upper()
        
        msg = f"{icon} *SIMULASYON ISLEMI* {icon}\\n\\n"
        msg += f"Hisse: #{clean_sym}\\n"
        msg += f"Islem: {action}\\n"
        msg += f"Fiyat: {price:.2f}\\n"
        msg += f"Saat: {time_str}\\n"
        
        if reason:
            msg += f"Aciklama: {reason}\\n"
        if pnl_pct is not None:
            msg += f"K/Z: %{round(pnl_pct, 2)}\\n"
            
        sent = self.send_telegram_message(msg)
        if sent:
            sent_trades.append(uid)
            with open(cache_file, "w") as f: json.dump(sent_trades[-500:], f)
        return sent

    def send_portfolio_alert(self, symbol: str, pnl_pct: float, action: str, price: float = None) -> bool:
        return False
'''

if start_idx != -1 and end_idx != -1:
    del lines[start_idx:end_idx]
    lines.insert(start_idx, new_code)
    with open('services/notification_manager.py', 'w', encoding='utf-8') as f:
        f.writelines(lines)
    print("DUZELTME_YAPILDI")
else:
    print("BULUNAMADI")
