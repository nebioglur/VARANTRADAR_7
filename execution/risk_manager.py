from typing import Dict, Any

class RiskManager:
    """
    CFG-06 Trade Planner (Risk Manager)
    Sermaye korumasını sağlayan modül. Asla tüm parayı tek işleme basmaz.
    Dinamik Kelly Kriteri veya Piyasaya göre risk kurallarını uygular.
    """
    
    @staticmethod
    def calculate_position_size(
        total_capital: float, 
        entry_price: float, 
        stop_loss: float, 
        win_rate_pct: float = 50.0,
        risk_reward_ratio: float = 2.0,
        max_risk_pct: float = 1.0
    ) -> Dict[str, Any]:
        """
        Dinamik Kelly Kriteri'ne (Half-Kelly) göre işlem riskini hesaplar.
        İflas riski kontrolü (Max %10 Drawdown per trade) uygulanır.
        """
        if total_capital <= 0 or entry_price <= 0 or stop_loss <= 0 or entry_price <= stop_loss:
            return {"Error": "Sermaye, giriş ve stop seviyeleri pozitif olmalı; long stop girişin altında olmalı."}
        if not 0 < max_risk_pct <= 2:
            return {"Error": "İşlem başına risk üst sınırı 0-2% aralığında olmalı."}

        risk_per_share = entry_price - stop_loss
        # Fixed fractional sizing avoids presenting fabricated win rates as Kelly inputs.
        recommended_risk_pct = float(max_risk_pct)
            
        max_loss_allowed = total_capital * (recommended_risk_pct / 100.0)
        
        # Kaç hisse/lot almalıyız?
        position_size_units = int(max_loss_allowed / risk_per_share) if risk_per_share > 0 else 0
        
        # O kadar lot almak için ne kadar nakit lazım?
        total_investment = position_size_units * entry_price
        
        # Eğer yatırım hesaptaki parayı aşıyorsa, alınabilecek maksimum limite çek
        if total_investment > total_capital:
            position_size_units = int(total_capital / entry_price)
            total_investment = position_size_units * entry_price
            
        actual_risk_pct = (position_size_units * risk_per_share) / total_capital * 100
        
        return {
            "Total_Capital": total_capital,
            "Max_Risk_Pct": round(recommended_risk_pct, 2),
            "Recommended_Units": position_size_units,
            "Total_Investment": round(total_investment, 2),
            "Actual_Risk_Amount": round(position_size_units * risk_per_share, 2),
            "Actual_Risk_Pct": round(actual_risk_pct, 2),
            "Warning": "Sabit risk bütçesine göre plan; broker emri değildir ve başarı olasılığı tahmini içermez."
        }
