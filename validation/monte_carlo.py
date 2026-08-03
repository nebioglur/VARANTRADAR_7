import random
from typing import Dict, Any

class MonteCarloSimulator:
    """
    CFG-07 Validation Layer (Monte Carlo)
    Sistemin ürettiği işlem planını (Stop/TP), binlerce farklı "rastgele kötü senaryoda" test eder.
    Amacı piyasa aniden çökerse portföyün iflas edip etmeyeceğini (Risk of Ruin) ölçmektir.
    """
    
    @staticmethod
    def run_simulation(win_rate: float, risk_reward: float, num_trades: int = 1000) -> Dict[str, Any]:
        """
        Girdi: Başarı oranı (%) ve Risk/Getiri oranı (Örn: 2.5).
        Çıktı: Maksimum ardışık kayıp serisi ve iflas riski.
        """
        
        current_capital = 100000.0 # Simüle edilmiş 100k bakiye
        risk_per_trade = 0.02 # Her işlemde kasanın %2'si riske ediliyor
        
        max_drawdown = 0.0
        peak_capital = current_capital
        consecutive_losses = 0
        max_consecutive_losses = 0
        
        for _ in range(num_trades):
            # Rastgele bir zar at (0-100 arası)
            roll = random.uniform(0, 100)
            
            trade_risk_amount = current_capital * risk_per_trade
            
            if roll <= win_rate:
                # İşlem Kazandı
                current_capital += (trade_risk_amount * risk_reward)
                consecutive_losses = 0
            else:
                # İşlem Kaybetti (Stop oldu)
                current_capital -= trade_risk_amount
                consecutive_losses += 1
                if consecutive_losses > max_consecutive_losses:
                    max_consecutive_losses = consecutive_losses
                    
            if current_capital > peak_capital:
                peak_capital = current_capital
            else:
                drawdown = (peak_capital - current_capital) / peak_capital * 100.0
                if drawdown > max_drawdown:
                    max_drawdown = drawdown
                    
            if current_capital <= 0:
                break
                
        risk_of_ruin = "YÜKSEK" if max_drawdown > 30 else ("ORTA" if max_drawdown > 15 else "DÜŞÜK")

        return {
            "Final_Capital": round(current_capital, 2),
            "Max_Drawdown_Pct": round(max_drawdown, 2),
            "Max_Consecutive_Losses": max_consecutive_losses,
            "Risk_of_Ruin": risk_of_ruin,
            "Verdict": "Güvenli Portföy Dağılımı." if max_drawdown < 20 else "Strateji çok riskli, pozisyon boyutunu düşür!"
        }
