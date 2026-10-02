import numpy as np
from typing import Dict, Any
from utils.logger import logger

class PositionSizingEngine:
    """
    Risk yönetimi ve optimum pozisyon büyüklüğü hesaplayan finansal motor.
    """
    
    @staticmethod
    def fixed_risk_sizing(capital: float, current_price: float, stop_loss: float, max_risk_pct: float = 0.02) -> Dict[str, Any]:
        """Sermayenin maksimum %X'ini riske atan klasik risk bazlı pozisyon büyüklüğü."""
        risk_per_unit = abs(current_price - stop_loss)
        if risk_per_unit <= 0:
            return {"quantity": 0, "investment": 0, "risk_amount": 0, "error": "Geçersiz Stop Loss"}
            
        max_risk_amount = capital * max_risk_pct
        units = int(max_risk_amount / risk_per_unit)
        total_investment = units * current_price
        
        if total_investment > capital:
            units = int(capital / current_price)
            total_investment = units * current_price
            
        return {
            "quantity": units,
            "investment": round(total_investment, 2),
            "risk_amount": round(units * risk_per_unit, 2)
        }

    @staticmethod
    def kelly_criterion_sizing(capital: float, current_price: float, win_rate: float, reward_to_risk: float, fraction: float = 0.5) -> Dict[str, Any]:
        """
        Kelly Kriteri: F = W - ((1 - W) / R)
        W = Win Rate (Örn: 0.55), R = Reward/Risk Ratio (Örn: 2.0)
        fraction = Half-Kelly (0.5) genelde aşırı riski önlemek için kullanılır.
        """
        if reward_to_risk <= 0:
            return {"quantity": 0, "investment": 0}
            
        kelly_pct = win_rate - ((1 - win_rate) / reward_to_risk)
        kelly_pct = max(0, min(kelly_pct, 1)) # Sınırlar 0-1 arası
        
        target_allocation_pct = kelly_pct * fraction
        investment = capital * target_allocation_pct
        units = int(investment / current_price)
        
        return {
            "quantity": units,
            "investment": round(units * current_price, 2),
            "kelly_pct": round(kelly_pct * 100, 2),
            "allocation_pct": round(target_allocation_pct * 100, 2)
        }
        
    @staticmethod
    def volatility_sizing(capital: float, current_price: float, atr: float, volatility_target_pct: float = 0.01) -> Dict[str, Any]:
        """ATR bazlı volatilite hedefleme (Trend Following stratejileri için)."""
        if atr <= 0:
            return {"quantity": 0, "investment": 0}
            
        target_cash_volatility = capital * volatility_target_pct
        units = int(target_cash_volatility / atr)
        total_investment = units * current_price
        
        if total_investment > capital:
            units = int(capital / current_price)
            total_investment = units * current_price
            
        return {
            "quantity": units,
            "investment": round(total_investment, 2)
        }
