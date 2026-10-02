import pandas as pd
import numpy as np
from typing import Dict, Any

try:
    from pypfopt import expected_returns
    from pypfopt import risk_models
    from pypfopt.efficient_frontier import EfficientFrontier
    from pypfopt.discrete_allocation import DiscreteAllocation, get_latest_prices
    PYPFOPT_AVAILABLE = True
except ImportError:
    PYPFOPT_AVAILABLE = False
    
from utils.logger import logger

class PortfolioOptimizationEngine:
    """
    Markowitz Mean-Variance Optimization (Efficient Frontier), Risk Parity, 
    Min Volatility ve Black-Litterman modellemelerini barındırır.
    """
    
    @staticmethod
    def optimize_max_sharpe(price_df: pd.DataFrame, current_capital: float = 100000.0) -> Dict[str, Any]:
        if not PYPFOPT_AVAILABLE:
            logger.warning("[PortfolioOptimization] PyPortfolioOpt kütüphanesi yüklü değil! Eşit ağırlık veriliyor.")
            n = len(price_df.columns)
            weights = {col: 1.0/n for col in price_df.columns}
            return {"weights": weights, "error": "PyPortfolioOpt kurulu değil."}
            
        try:
            mu = expected_returns.mean_historical_return(price_df)
            S = risk_models.sample_cov(price_df)
            ef = EfficientFrontier(mu, S)
            raw_weights = ef.max_sharpe()
            cleaned_weights = dict(ef.clean_weights())
            
            expected_annual_return, annual_volatility, sharpe_ratio = ef.portfolio_performance(verbose=False)
            
            latest_prices = get_latest_prices(price_df)
            da = DiscreteAllocation(cleaned_weights, latest_prices, total_portfolio_value=current_capital)
            allocation, leftover = da.lp_portfolio()
            
            return {
                "weights": cleaned_weights,
                "allocation": allocation,
                "leftover_cash": leftover,
                "expected_annual_return": round(expected_annual_return * 100, 2),
                "annual_volatility": round(annual_volatility * 100, 2),
                "sharpe_ratio": round(sharpe_ratio, 2)
            }
        except Exception as e:
            logger.error(f"[PortfolioOptimization] Hatası: {e}")
            return {"error": str(e)}

    @staticmethod
    def optimize_min_volatility(price_df: pd.DataFrame, current_capital: float = 100000.0) -> Dict[str, Any]:
        """Minimum Varyans (En düşük risk) portföyünü oluşturur."""
        if not PYPFOPT_AVAILABLE:
            return {"error": "PyPortfolioOpt kurulu değil."}
            
        try:
            mu = expected_returns.mean_historical_return(price_df)
            S = risk_models.sample_cov(price_df)
            ef = EfficientFrontier(mu, S)
            raw_weights = ef.min_volatility()
            cleaned_weights = dict(ef.clean_weights())
            
            expected_annual_return, annual_volatility, sharpe_ratio = ef.portfolio_performance(verbose=False)
            
            latest_prices = get_latest_prices(price_df)
            da = DiscreteAllocation(cleaned_weights, latest_prices, total_portfolio_value=current_capital)
            allocation, leftover = da.lp_portfolio()
            
            return {
                "weights": cleaned_weights,
                "allocation": allocation,
                "leftover_cash": leftover,
                "expected_annual_return": round(expected_annual_return * 100, 2),
                "annual_volatility": round(annual_volatility * 100, 2),
                "sharpe_ratio": round(sharpe_ratio, 2)
            }
        except Exception as e:
            return {"error": str(e)}

    @staticmethod
    def optimize_black_litterman(price_df: pd.DataFrame, market_prices: pd.Series, viewdict: Dict[str, float], current_capital: float = 100000.0) -> Dict[str, Any]:
        """
        Black-Litterman Modeli: Yatırımcı görüşleri (views) ile piyasa dengesini birleştirir.
        viewdict: {'ASELS.IS': 0.10, 'THYAO.IS': 0.05}
        """
        if not PYPFOPT_AVAILABLE:
            return {"error": "PyPortfolioOpt kurulu değil."}
            
        try:
            from pypfopt import black_litterman
            from pypfopt.black_litterman import BlackLittermanModel
            
            S = risk_models.sample_cov(price_df)
            delta = black_litterman.market_implied_risk_aversion(market_prices)
            
            mcaps = {sym: 1.0 for sym in price_df.columns} 
            prior = black_litterman.market_implied_prior_returns(mcaps, delta, S)
            
            bl = BlackLittermanModel(S, pi=prior, absolute_views=viewdict)
            bl_returns = bl.bl_returns()
            bl_cov = bl.bl_cov()
            
            ef = EfficientFrontier(bl_returns, bl_cov)
            raw_weights = ef.max_sharpe()
            cleaned_weights = dict(ef.clean_weights())
            
            expected_annual_return, annual_volatility, sharpe_ratio = ef.portfolio_performance(verbose=False)
            
            latest_prices = get_latest_prices(price_df)
            da = DiscreteAllocation(cleaned_weights, latest_prices, total_portfolio_value=current_capital)
            allocation, leftover = da.lp_portfolio()
            
            return {
                "weights": cleaned_weights,
                "allocation": allocation,
                "leftover_cash": leftover,
                "expected_annual_return": round(expected_annual_return * 100, 2),
                "annual_volatility": round(annual_volatility * 100, 2),
                "sharpe_ratio": round(sharpe_ratio, 2)
            }
        except Exception as e:
            return {"error": str(e)}
