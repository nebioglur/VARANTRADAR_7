import numpy as np
import math

def norm_cdf(x):
    """Cumulative distribution function for the standard normal distribution."""
    return (1.0 + math.erf(x / math.sqrt(2.0))) / 2.0

def norm_pdf(x):
    """Probability density function for the standard normal distribution."""
    return math.exp(-x**2 / 2.0) / math.sqrt(2.0 * math.pi)

class WarrantMath:
    @staticmethod
    def black_scholes_call(S, K, T, r, sigma):
        """ Calculate Call option price using Black-Scholes """
        if T <= 0: return max(0.0, S - K)
        d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)
        return S * norm_cdf(d1) - K * np.exp(-r * T) * norm_cdf(d2)

    @staticmethod
    def black_scholes_put(S, K, T, r, sigma):
        """ Calculate Put option price using Black-Scholes """
        if T <= 0: return max(0.0, K - S)
        d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)
        return K * np.exp(-r * T) * norm_cdf(-d2) - S * norm_cdf(-d1)
        
    @staticmethod
    def calculate_greeks(S, K, T, r, sigma, option_type='CALL'):
        if T <= 0:
            return {'delta': 0, 'gamma': 0, 'theta': 0, 'vega': 0}
            
        d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)
        
        gamma = norm_pdf(d1) / (S * sigma * np.sqrt(T))
        vega = S * norm_pdf(d1) * np.sqrt(T)
        
        if option_type.upper() == 'CALL':
            delta = norm_cdf(d1)
            theta = (-S * norm_pdf(d1) * sigma / (2 * np.sqrt(T))) - (r * K * np.exp(-r * T) * norm_cdf(d2))
        else:
            delta = norm_cdf(d1) - 1
            theta = (-S * norm_pdf(d1) * sigma / (2 * np.sqrt(T))) + (r * K * np.exp(-r * T) * norm_cdf(-d2))
            
        return {
            'delta': delta,
            'gamma': gamma,
            'theta': theta / 365.0, # Daily theta
            'vega': vega / 100.0 # 1% volatility change
        }
