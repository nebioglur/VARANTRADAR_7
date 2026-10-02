import pandas as pd
import numpy as np
from typing import Dict, Any

class MonteCarloEngine:
    """
    Strateji getirileri üzerinden 10.000 rastgele simülasyon (Random Walk / Resampling)
    yaparak olası gelecek senaryolarını hesaplar.
    """
    
    @staticmethod
    def run_simulation(bt_df: pd.DataFrame, num_simulations: int = 1000, forecast_days: int = 252) -> Dict[str, Any]:
        """
        Geçmiş günlük getirilerden rastgele örneklem çekerek gelecekteki olası
        sermaye büyümesini simüle eder.
        """
        if bt_df.empty or 'strategy_returns' not in bt_df.columns:
            return {}
            
        returns = bt_df['strategy_returns'].fillna(0).values
        if len(returns) < 50:
            return {"error": "Simülasyon için yeterli geçmiş getiri yok (min 50 gün)."}
            
        initial_capital = bt_df['strategy_equity'].iloc[-1]
        
        # Simülasyon Matrisi (Monte Carlo)
        # Her sütun bir simülasyon (1000), her satır bir gün (252)
        simulated_returns = np.random.choice(returns, size=(forecast_days, num_simulations), replace=True)
        
        # Sermaye Yolu (Equity Paths)
        # (1 + R) kümülatif çarpımı
        price_paths = initial_capital * np.cumprod(1 + simulated_returns, axis=0)
        
        # Son günkü değerler (Bitiş sermayeleri)
        final_values = price_paths[-1, :]
        
        # İstatistikler
        mean_ending_capital = np.mean(final_values)
        median_ending_capital = np.median(final_values)
        worst_case_99 = np.percentile(final_values, 1) # %99 VaR bölgesi
        best_case_1 = np.percentile(final_values, 99)
        win_probability = np.sum(final_values > initial_capital) / num_simulations * 100
        
        return {
            "Simulations": num_simulations,
            "Forecast_Days": forecast_days,
            "Initial_Capital": round(initial_capital, 2),
            "Mean_Final_Capital": round(mean_ending_capital, 2),
            "Median_Final_Capital": round(median_ending_capital, 2),
            "Worst_Case_1_Percent": round(worst_case_99, 2),
            "Best_Case_1_Percent": round(best_case_1, 2),
            "Probability_of_Profit": round(win_probability, 2),
            # Grafik çizimi için örneklem yolları (ilk 50 senaryo) UI tarafında gösterilebilir
            "Sample_Paths": price_paths[:, :50].tolist() 
        }
