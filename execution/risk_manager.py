from typing import Dict, Any
import math


class RiskManager:
    """Conservative long-only position sizing with explicit input validation."""

    @staticmethod
    def calculate_position_size(
        total_capital: float,
        entry_price: float,
        stop_loss: float,
        win_rate_pct: float = 55.0,
        risk_reward_ratio: float = 2.0,
        max_risk_pct: float = 1.0,
    ) -> Dict[str, Any]:
        values = (total_capital, entry_price, stop_loss, win_rate_pct, risk_reward_ratio, max_risk_pct)
        if not all(isinstance(v, (int, float)) and math.isfinite(float(v)) for v in values):
            return {"Error": "Tüm girdiler sonlu sayısal değer olmalıdır."}
        if total_capital <= 0 or entry_price <= 0 or stop_loss <= 0:
            return {"Error": "Sermaye, giriş ve stop fiyatı sıfırdan büyük olmalıdır."}
        if entry_price <= stop_loss:
            return {"Error": "Long işlemde stop fiyatı giriş fiyatından düşük olmalıdır."}
        if not 0 <= win_rate_pct <= 100 or risk_reward_ratio <= 0:
            return {"Error": "Kazanma oranı 0-100, risk/getiri oranı sıfırdan büyük olmalıdır."}
        if not 0 < max_risk_pct <= 1.0:
            return {"Error": "İşlem başına azami risk %1 ile sınırlandırılmıştır."}

        # Half-Kelly fraction, expressed as a fraction of capital at risk.
        win_probability = win_rate_pct / 100.0
        kelly_fraction = win_probability - ((1.0 - win_probability) / risk_reward_ratio)
        half_kelly_pct = max(0.0, kelly_fraction / 2.0 * 100.0)
        allowed_risk_pct = min(half_kelly_pct, max_risk_pct)

        # No positive edge means no trade; do not force a fictitious minimum position.
        if allowed_risk_pct <= 0:
            return {
                "Total_Capital": float(total_capital),
                "Max_Risk_Pct": 0.0,
                "Recommended_Units": 0,
                "Total_Investment": 0.0,
                "Actual_Risk_Amount": 0.0,
                "Actual_Risk_Pct": 0.0,
                "Warning": "Pozitif Kelly avantajı yok; işlem açılmamalı."
            }

        risk_per_share = entry_price - stop_loss
        risk_budget = total_capital * allowed_risk_pct / 100.0
        units_by_risk = math.floor(risk_budget / risk_per_share)
        units_by_cash = math.floor(total_capital / entry_price)
        units = max(0, min(units_by_risk, units_by_cash))
        investment = units * entry_price
        actual_risk = units * risk_per_share
        actual_risk_pct = actual_risk / total_capital * 100.0

        return {
            "Total_Capital": float(total_capital),
            "Max_Risk_Pct": round(allowed_risk_pct, 4),
            "Recommended_Units": units,
            "Total_Investment": round(investment, 2),
            "Actual_Risk_Amount": round(actual_risk, 2),
            "Actual_Risk_Pct": round(actual_risk_pct, 4),
            "Warning": "Half-Kelly; işlem başına azami sermaye riski %1. Komisyon, kayma ve gap riski ayrıca hesaba katılmalıdır."
        }
