# -*- coding: utf-8 -*-
import re

with open('services/notification_manager.py', 'r', encoding='utf-8') as f:
    content = f.read()

vip_code = '''
VIP_SYMBOLS = [
    "AKBNK", "ALARK", "ASELS", "ASTOR", "BIMAS", "BRSAN", "DOAS", "EGEEN", 
    "EKGYO", "ENKAI", "EREGL", "FROTO", "GARAN", "GUBRF", "HEKTS", "ISCTR", "KCHOL", 
    "KONTR", "KOZAA", "KOZAL", "KRDMD", "ODAS", "OYAKC", "PETKM", "PGSUS", "SAHOL", 
    "SASA", "SISE", "TAVHL", "TCELL", "THYAO", "TOASO", "TUPRS", "VAKBN", "YKBNK"
]

def is_vip(symbol):
    clean = symbol.replace(".IS", "").upper()
    return clean in VIP_SYMBOLS

'''

tavan_pattern = re.compile(r"def send_tavan_alert\(self.*?\) -> bool:.*?(?=def |$)", re.DOTALL)
new_tavan = '''def send_tavan_alert(self, symbol: str, score: int, reason: str, position: dict = None, extra: dict = None) -> bool:
        if not is_vip(symbol):
            return False
        
        clean_sym = symbol.replace(".IS", "").upper()
        msg = f"🚀 <b>VIP TAVAN ADAYI</b> 🚀\\n\\n"
        msg += f"👑 <b>Hisse:</b> #{clean_sym}\\n"
        msg += f"🎯 <b>Puan:</b> {score}/100\\n"
        msg += f"📊 <b>Neden:</b> {reason}\\n"
        
        if extra and "Price" in extra:
            msg += f"💰 <b>Fiyat:</b> {float(extra['Price']):.2f}\\n"
            
        msg += f"\\n🤖 <i>VarantRadar VIP Motoru</i>"
        return self.send_telegram_message(msg)
'''

radar_pattern = re.compile(r"def send_radar_alert\(self.*?\) -> bool:.*?(?=def |$)", re.DOTALL)
new_radar = '''def send_radar_alert(self, symbol: str, score: int, level: str, reason: str, price: float = None, change_pct: float = None) -> bool:
        if not is_vip(symbol): return False
        
        clean_sym = symbol.replace(".IS", "").upper()
        msg = f"💎 <b>VIP RADAR FIRSATI</b> 💎\\n\\n"
        msg += f"👑 <b>Hisse:</b> #{clean_sym}\\n"
        if price is not None:
            chg_str = f" (%+{change_pct:.2f})" if change_pct and change_pct > 0 else (f" (%{change_pct:.2f})" if change_pct else "")
            msg += f"💰 <b>Fiyat:</b> {price:.2f}{chg_str}\\n"
        msg += f"🎯 <b>Puan:</b> {score}/100\\n"
        msg += f"📊 <b>Seviye:</b> {level}\\n"
        msg += f"📝 <b>Neden:</b> {reason}\\n\\n"
        msg += f"🤖 <i>VarantRadar VIP Motoru</i>"
        return self.send_telegram_message(msg)
'''

sim_pattern = re.compile(r"def send_simulation_trade_alert\(self.*?\) -> bool:.*?(?=def |$)", re.DOTALL)
new_sim = '''def send_simulation_trade_alert(self, symbol: str, action: str, price: float, time_str: str, pnl_pct: float = None, reason: str = "") -> bool:
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
        
        clean_sym = symbol.replace(".IS", "").upper()
        
        if "AL" in action or action == "ENTER":
            icon = "🟢"
            title = "OTOMATIK ALIM EMRI"
        elif "KAR" in action or "TP" in action:
            icon = "🔵"
            title = "OTOMATIK KAR AL EMRI"
        elif "STOP" in action or "ZARAR" in action:
            icon = "🔴"
            title = "OTOMATIK STOP-LOSS EMRI"
        else:
            icon = "🟠"
            title = "OTOMATIK SATIS EMRI"
            
        msg = f"{icon} <b>SIMULASYON: {title}</b> {icon}\\n\\n"
        msg += f"📌 <b>Hisse:</b> #{clean_sym}\\n"
        msg += f"⚡ <b>Islem Tipi:</b> <b>{action}</b>\\n"
        msg += f"💰 <b>Gerceklesen Fiyat:</b> <b>{float(price):.2f} TL</b>\\n"
        msg += f"⏱ <b>Emir Saati:</b> {time_str}\\n"
        
        if reason:
            msg += f"📝 <b>Strateji & Neden:</b> <i>{reason}</i>\\n"
            
        if pnl_pct is not None:
            pnl_icon = "🔥" if pnl_pct > 0 else "🩸"
            msg += f"{pnl_icon} <b>Kar/Zarar:</b> %{round(pnl_pct, 2)}\\n"
            
        msg += f"\\n🤖 <i>VarantRadar V8 AI Algoritmasi</i>"
            
        sent = self.send_telegram_message(msg)
        if sent:
            sent_trades.append(uid)
            try:
                os.makedirs("data", exist_ok=True)
                with open(cache_file, "w") as f: json.dump(sent_trades, f)
            except: pass
        return sent
'''

content = re.sub(r"def send_1h_opportunity_alert\(self, opp: dict\) -> bool:", "def send_1h_opportunity_alert(self, opp: dict) -> bool:\\n        if not is_vip(opp.get('Symbol', '')): return False", content)
content = re.sub(r"def send_5m_rsi_alert\(self, symbol: str, signal: str, rsi: float, price: float\) -> bool:", "def send_5m_rsi_alert(self, symbol: str, signal: str, rsi: float, price: float) -> bool:\\n        if not is_vip(symbol): return False", content)

content = re.sub(tavan_pattern, new_tavan, content)
content = re.sub(radar_pattern, new_radar, content)
content = re.sub(sim_pattern, new_sim, content)

content = content.replace("class NotificationManager:", vip_code + "\\nclass NotificationManager:")

with open('services/notification_manager.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("PATCH_NOTIF_MANAGER_OK")
