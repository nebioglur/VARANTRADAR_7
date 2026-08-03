import pandas as pd
import numpy as np
from typing import Dict, Any

class AttributionEngine:
    """
    Portföy Getiri ve Risk Kaynağı (Attribution) Analizi.
    """
    
    @staticmethod
    def calculate_risk_contribution(weights: Dict[str, float], cov_matrix: pd.DataFrame) -> Dict[str, Any]:
        """
        Marginal Contribution to Risk (MCR) ve Component Contribution to Risk (CCR).
        Portföydeki riskin tam olarak hangi hisseden geldiğini (% olarak) hesaplar.
        """
        if not weights or cov_matrix.empty:
            return {}
            
        assets = list(cov_matrix.columns)
        w = np.array([weights.get(a, 0) for a in assets])
        
        if w.sum() == 0:
            return {}
            
        # Portföy Varyansı ve Volatilitesi
        port_var = np.dot(w.T, np.dot(cov_matrix, w))
        port_vol = np.sqrt(port_var)
        
        if port_vol == 0:
            return {}
            
        # Marjinal Risk Katkısı (MCR) = (Cov * w) / Port_Vol
        mcr = np.dot(cov_matrix, w) / port_vol
        
        # Yüzdesel Risk Katkısı (Percentage Risk Contribution)
        # PCR = (w * MCR) / Port_Vol
        pcr = (w * mcr) / port_vol
        
        results = {}
        for i, asset in enumerate(assets):
            results[asset] = {
                "Weight": round(w[i] * 100, 2),
                "Marginal_Risk_Contribution": round(mcr[i] * 100, 4),
                "Percentage_Risk_Contribution": round(pcr[i] * 100, 2)
            }
            
        return results

    @staticmethod
    def calculate_return_attribution(portfolio_returns: pd.Series, benchmark_returns: pd.Series) -> Dict[str, float]:
        """
        Basitleştirilmiş Alpha ve Beta (Treynor-Black vb. yaklaşımlar için temel).
        Aktif getiri (Active Return = Portföy - Benchmark) analizi.
        """
        if portfolio_returns.empty or benchmark_returns.empty:
            return {}
            
        # İki seriyi aynı tarihlere (index) hizala
        df = pd.concat([portfolio_returns, benchmark_returns], axis=1).dropna()
        df.columns = ['Portfolio', 'Benchmark']
        
        if df.empty:
            return {}
            
        port_ret = df['Portfolio'].sum()
        bench_ret = df['Benchmark'].sum()
        active_return = port_ret - bench_ret
        
        # Beta hesaplama (Cov(P, B) / Var(B))
        cov_matrix = df.cov()
        beta = cov_matrix.iloc[0, 1] / cov_matrix.iloc[1, 1] if cov_matrix.iloc[1, 1] != 0 else 1.0
        
        # Jensen's Alpha (Basit)
        # Alpha = R_p - [R_f + Beta * (R_m - R_f)]
        # R_f (Risk free) basitleştirme amaçlı 0 alındı (Günlük)
        alpha = df['Portfolio'].mean() - (beta * df['Benchmark'].mean())
        annualized_alpha = alpha * 252
        
        return {
            "Total_Portfolio_Return": round(port_ret * 100, 2),
            "Total_Benchmark_Return": round(bench_ret * 100, 2),
            "Active_Return": round(active_return * 100, 2),
            "Portfolio_Beta": round(beta, 2),
            "Annualized_Alpha": round(annualized_alpha * 100, 2)
        }
