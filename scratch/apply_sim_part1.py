import os

with open('services/simulation_engine.py', 'r', encoding='utf-8') as f:
    code = f.read()

# 1. Patch _position_allocation
old_alloc = """    def _position_allocation(self, current_cash, entry_price, stop_price, is_bear, risk_pct=None):
        risk_per_share = entry_price - stop_price
        if risk_per_share <= 0:
            return 0.0, 0.0

        # DINAMIK RISK: senaryo risk_pct (G\u00dc\u00c7L\u00dc BO\u011eA %2.0, BO\u011eA %1.5, N\u00d6TR
        # %1.0) verilirse o kullanilir; yoksa eski sabit davranis.
        if risk_pct and risk_pct > 0:
            risk_budget = self.daily_budget * risk_pct
        else:
            risk_budget = self.daily_budget * (0.005 if is_bear else 0.012)
        max_notional = self.daily_budget * (0.15 if is_bear else 0.33)
        risk_limited_notional = risk_budget * entry_price / risk_per_share
        allocation = min(current_cash, max_notional, risk_limited_notional)
        return allocation, min(risk_budget, allocation * risk_per_share / entry_price)"""

new_alloc = """    def _position_allocation(self, current_cash, entry_price, stop_price, is_bear, risk_pct=None, regime="NEUTRAL", open_slots=1):
        risk_per_share = entry_price - stop_price
        if risk_per_share <= 0:
            return 0.0, 0.0

        # KULLANICI ISTEGI: Nakitte para yatmasin, ozellikle BIST boga iken olabildigince aktif ofansif trade!
        is_strong_bull = (regime == "STRONG_BULL" or "\u00dc\u00c7L\u00dc" in str(regime))
        is_bull = (is_strong_bull or regime == "BULL" or "BO\u011eA" in str(regime))

        if risk_pct and risk_pct > 0:
            risk_budget = self.daily_budget * risk_pct
        else:
            if is_strong_bull:
                risk_budget = self.daily_budget * 0.022
            elif is_bull:
                risk_budget = self.daily_budget * 0.018
            elif is_bear:
                risk_budget = self.daily_budget * 0.005
            else:
                risk_budget = self.daily_budget * 0.012

        slots = max(1, open_slots)
        slot_target = current_cash / slots

        if is_strong_bull:
            max_notional = min(current_cash, max(slot_target, self.daily_budget * 0.50))
        elif is_bull:
            max_notional = min(current_cash, max(slot_target, self.daily_budget * 0.40))
        elif is_bear:
            max_notional = self.daily_budget * 0.15
        else:
            max_notional = min(current_cash, max(slot_target, self.daily_budget * 0.35))

        risk_limited_notional = risk_budget * entry_price / max(0.001, risk_per_share)
        
        # Boga modunda nakitin atil kalmasini engellemek icin slot_target'a oncelik verilir
        if is_bull and current_cash > 0:
            preferred_notional = max(slot_target, risk_limited_notional)
            allocation = min(current_cash, max_notional, preferred_notional)
        else:
            allocation = min(current_cash, max_notional, risk_limited_notional)

        return allocation, min(risk_budget, allocation * risk_per_share / entry_price)"""

assert old_alloc in code, "old_alloc not found in code"
code = code.replace(old_alloc, new_alloc, 1)

with open('services/simulation_engine.py', 'w', encoding='utf-8', newline='') as f:
    f.write(code)

print("services/simulation_engine.py part 1 patched!")
