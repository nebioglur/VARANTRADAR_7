# -*- coding: utf-8 -*-
import sys

with open('services/notification_manager.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_str = '''    def send_portfolio_alert(self, symbol: str, pnl_pct: float, action: str, price: float = None) -> bool:'''
new_str = '''    def send_simulation_trade_alert(self, symbol: str, action: str, price: float, time_str: str, pnl_pct: float = None, reason: str = "") -> bool:
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
        icon = "🟢" if action.startswith("AL") else "🔴"
        clean_sym = symbol.replace(".IS", "").upper()
        msg = f"{icon} <b>ÇELİK SİMÜLASYON İŞLEMİ</b> {icon}\n\n📌 <b>Hisse:</b> #{clean_sym}\n⚡ <b>İşlem:</b> {action}\n💰 <b>Fiyat:</b> ₺{price:.2f}\n🕒 <b>Saat:</b> {time_str}\n"
        if reason: msg += f"📋 <b>Açıklama:</b> {reason}\n"
        if pnl_pct is not None: msg += f"📊 <b>İşlem K/Z:</b> %{round(pnl_pct, 2)}\n"
        sent = self.send_telegram_message(msg)
        if sent:
            sent_trades.append(uid)
            with open(cache_file, "w") as f: json.dump(sent_trades[-500:], f)
        return sent

    def send_portfolio_alert(self, symbol: str, pnl_pct: float, action: str, price: float = None) -> bool:
        return False'''

content = content.replace(old_str, new_str)

with open('services/notification_manager.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("YAZILDI")
