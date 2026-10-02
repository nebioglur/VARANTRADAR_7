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
        win_rate_pct: float = 55.0,
        risk_reward_ratio: float = 2.0
    ) -> Dict[str, Any]:
        """
        Dinamik Kelly Kriteri'ne (Half-Kelly) göre işlem riskini hesaplar.
        İflas riski kontrolü (Max %10 Drawdown per trade) uygulanır.
        """
        if entry_price <= stop_loss:
            return {"Error": "Stop-Loss, giriş fiyatından büyük/eşit olamaz (Long işlem için)."}
            
        risk_per_share = entry_price - stop_loss
        
        # Kelly Formülü: K = W - [(1 - W) / R]
        # W: Win Probability (0 to 1)
        # R: Risk/Reward Ratio
        w = win_rate_pct / 100.0
        r = risk_reward_ratio
        
        kelly_pct = w - ((1 - w) / r) if r > 0 else 0
        
        # Half-Kelly (Daha muhafazakar bir yaklaşım)
        recommended_risk_pct = (kelly_pct / 2.0) * 100
        
        # Sınırlandırmalar (Min %1, Max %10 kuralı)
        if recommended_risk_pct <= 0:
            recommended_risk_pct = 1.0 # İstatistiksel eksi çıksa bile 1 lotluk minimum test denemesi
        elif recommended_risk_pct > 10.0:
            recommended_risk_pct = 10.0 # Sermaye Koruması: Hiçbir işleme %10'dan fazla risk alma!
            
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
            "Warning": "Kelly Kriteri (Half-Kelly) ile optimize edilmiştir."
        }
