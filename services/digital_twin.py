import pandas as pd
import numpy as np

class DigitalMarketTwin:
    """
    VarantRadar X (V12) - Digital Market Twin & Quant Lab
    Gerçek piyasa verileri üzerinde Monte Carlo simülasyonları ve Stres Testleri uygular.
    """
    
    @staticmethod
    def run_stress_test(df: pd.DataFrame, shock_type: str = "Volatility") -> dict:
        """
        Piyasada ani bir kriz/şok senaryosu simüle eder (Digital Twin).
        """
        if df.empty or len(df) < 20:
            return {"status": "Yetersiz Veri", "survivability_score": 0}
            
        current_price = df['close'].iloc[-1]
        daily_returns = df['close'].pct_change().dropna()
        
        # Monte Carlo Simülasyonu (Gelecek 30 gün için 100 farklı senaryo)
        days = 30
        simulations = 100
        
        mean_return = daily_returns.mean()
        std_return = daily_returns.std()
        
        # Şok Senaryoları (Regime Shift)
        if shock_type == "Volatility":
            std_return *= 2.5  # Volatiliteyi 2.5 katına çıkar
        elif shock_type == "Crash":
            mean_return = -abs(mean_return) * 5  # Sürekli düşüş trendi
        
        simulated_prices = np.zeros((days, simulations))
        simulated_prices[0] = current_price
        
        for t in range(1, days):
            # Rastgele şoklar (Normal dağılım)
            random_shocks = np.random.normal(mean_return, std_return, simulations)
            simulated_prices[t] = simulated_prices[t-1] * (1 + random_shocks)
            
        # Sonuç Analizi
        final_prices = simulated_prices[-1]
        max_loss = (current_price - np.min(final_prices)) / current_price * 100
        avg_price = np.mean(final_prices)
        
        survivability = 100 - min(100, max_loss)
        
        return {
            "Simulation_Days": days,
            "Paths_Generated": simulations,
            "Max_Expected_Loss_Pct": round(max_loss, 2),
            "Average_Forecast_Price": round(avg_price, 2),
            "Survivability_Score": round(survivability, 1),
            "Scenario": shock_type,
            "Note": "Dijital ikiz şok simülasyonu tamamlandı."
        }
