import pandas as pd
import itertools
from typing import Dict, Any, Callable
from engines.backtest_engine import BacktestEngine
from engines.performance_engine import PerformanceEngine
from utils.logger import logger

class OptimizationEngine:
    """
    Strateji parametrelerini (Örn: EMA Fast, EMA Slow) grid search yöntemiyle 
    test ederek en iyi Sharpe/CAGR oranını veren kombinasyonu bulur.
    """
    
    @staticmethod
    def run_grid_search(df: pd.DataFrame, strategy_func: Callable, param_grid: Dict[str, list], target_metric: str = "Sharpe_Ratio") -> Dict[str, Any]:
        """
        Örnek param_grid: {"fast_period": [10, 20, 30], "slow_period": [50, 100, 200]}
        """
        keys = list(param_grid.keys())
        values = list(param_grid.values())
        combinations = list(itertools.product(*values))
        
        best_metric = -float('inf')
        best_params = {}
        best_bt_df = pd.DataFrame()
        best_performance = {}
        
        backtester = BacktestEngine(initial_capital=100000.0)
        
        logger.info(f"[OptimizationEngine] Grid search started. Total combinations: {len(combinations)}")
        
        for combo in combinations:
            params = dict(zip(keys, combo))
            
            # Sinyal Üret
            try:
                signals = strategy_func(df, **params)
            except Exception as e:
                continue
                
            # Backtest
            bt_df = backtester.run_backtest(df, signals)
            
            # Performans Ölçümü
            perf = PerformanceEngine.calculate_metrics(bt_df)
            if not perf:
                continue
                
            current_metric = perf.get(target_metric, -float('inf'))
            
            # Maximization problemi varsayımı (Eğer Max_Drawdown minimize edilecekse mantık değişir)
            if target_metric == "Max_Drawdown":
                # Drawdown genelde negatif gösterilir, -20% vs -10% (daha yüksek olan, yani -10% daha iyidir)
                pass # Normal büyüktür mantığı çalışır (-10 > -20)
                
            if current_metric > best_metric:
                best_metric = current_metric
                best_params = params
                best_bt_df = bt_df
                best_performance = perf
                
        logger.info(f"[OptimizationEngine] Grid search complete. Best {target_metric}: {best_metric}")
        
        return {
            "Best_Parameters": best_params,
            "Best_Metrics": best_performance,
            # UI'da göstermek için best_bt_df equity eğrisi kullanılabilir.
        }
