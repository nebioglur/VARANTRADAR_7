import pandas as pd
import numpy as np
from typing import Dict, Any

class PerformanceEngine:
    """
    Backtest sonuçlarından istatistiksel Quant metrikleri (Sharpe, CAGR vb.) hesaplar.
    """
    
    @staticmethod
    def calculate_metrics(bt_df: pd.DataFrame, risk_free_rate: float = 0.02) -> Dict[str, Any]:
        if bt_df.empty or 'strategy_returns' not in bt_df.columns:
            return {}
            
        returns = bt_df['strategy_returns'].fillna(0)
        equity = bt_df['strategy_equity']
        
        # Toplam Getiri
        total_return = (equity.iloc[-1] / equity.iloc[0]) - 1
        
        # CAGR (Compound Annual Growth Rate)
        days = (bt_df.index[-1] - bt_df.index[0]).days
        years = days / 365.25 if days > 0 else 1
        cagr = ((equity.iloc[-1] / equity.iloc[0]) ** (1 / years)) - 1 if years > 0 else 0
        
        # Sharpe Oranı
        daily_rf = risk_free_rate / 252
        excess_returns = returns - daily_rf
        mean_excess = excess_returns.mean()
        std_excess = returns.std()
        sharpe = (mean_excess / std_excess) * np.sqrt(252) if std_excess > 0 else 0
        
        # Sortino Oranı (Sadece negatif getirilerin standart sapması)
        negative_returns = returns[returns < 0]
        std_negative = negative_returns.std()
        sortino = (mean_excess / std_negative) * np.sqrt(252) if std_negative > 0 else 0
        
        # Maximum Drawdown
        running_max = np.maximum.accumulate(equity)
        drawdown = (equity - running_max) / running_max
        max_drawdown = drawdown.min()
        
        # Calmar Oranı
        calmar = cagr / abs(max_drawdown) if max_drawdown < 0 else np.inf
        
        # Win Rate
        trades = bt_df[bt_df['trades'] > 0]
        # Basit hesaplama: Günlük bazda kazanma oranı (gerçek trade win rate için sinyal eşleşmesi gerekir)
        winning_days = len(returns[returns > 0])
        total_active_days = len(returns[returns != 0])
        win_rate = winning_days / total_active_days if total_active_days > 0 else 0
        
        return {
            "Total_Return": round(total_return * 100, 2),
            "CAGR": round(cagr * 100, 2),
            "Sharpe_Ratio": round(sharpe, 2),
            "Sortino_Ratio": round(sortino, 2),
            "Calmar_Ratio": round(calmar, 2),
            "Max_Drawdown": round(max_drawdown * 100, 2),
            "Win_Rate": round(win_rate * 100, 2)
        }
