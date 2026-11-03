import math
import numpy as np


def norm_cdf(x):
    return (1.0 + math.erf(float(x) / math.sqrt(2.0))) / 2.0


def norm_pdf(x):
    return math.exp(-(float(x) ** 2) / 2.0) / math.sqrt(2.0 * math.pi)


class WarrantMath:
    @staticmethod
    def _inputs(S, K, T, r, sigma):
        values = [S, K, T, r, sigma]
        if not all(isinstance(v, (int, float, np.number)) and math.isfinite(float(v)) for v in values):
            raise ValueError("Black-Scholes inputs must be finite numbers")
        S, K, T, r, sigma = map(float, values)
        if S <= 0 or K <= 0 or T < 0 or sigma < 0:
            raise ValueError("S and K must be positive; T and sigma must be non-negative")
        return S, K, T, r, sigma

    @staticmethod
    def black_scholes_call(S, K, T, r, sigma):
        S, K, T, r, sigma = WarrantMath._inputs(S, K, T, r, sigma)
        if T == 0:
            return max(0.0, S - K)
        if sigma == 0:
            return max(0.0, S - K * math.exp(-r * T))
        root_t = math.sqrt(T)
        d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * root_t)
        d2 = d1 - sigma * root_t
        return S * norm_cdf(d1) - K * math.exp(-r * T) * norm_cdf(d2)

    @staticmethod
    def black_scholes_put(S, K, T, r, sigma):
        S, K, T, r, sigma = WarrantMath._inputs(S, K, T, r, sigma)
        if T == 0:
            return max(0.0, K - S)
        if sigma == 0:
            return max(0.0, K * math.exp(-r * T) - S)
        root_t = math.sqrt(T)
        d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * root_t)
        d2 = d1 - sigma * root_t
        return K * math.exp(-r * T) * norm_cdf(-d2) - S * norm_cdf(-d1)

    @staticmethod
    def calculate_greeks(S, K, T, r, sigma, option_type="CALL"):
        S, K, T, r, sigma = WarrantMath._inputs(S, K, T, r, sigma)
        option_type = str(option_type).upper()
        if option_type not in {"CALL", "PUT"}:
            raise ValueError("option_type must be CALL or PUT")
        if T == 0 or sigma == 0:
            if option_type == "CALL":
                delta = 1.0 if S > K else 0.0
            else:
                delta = -1.0 if S < K else 0.0
            return {"delta": delta, "gamma": 0.0, "theta": 0.0, "vega": 0.0}

        root_t = math.sqrt(T)
        d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * root_t)
        d2 = d1 - sigma * root_t
        gamma = norm_pdf(d1) / (S * sigma * root_t)
        vega = S * norm_pdf(d1) * root_t / 100.0

        if option_type == "CALL":
            delta = norm_cdf(d1)
            theta_annual = -(S * norm_pdf(d1) * sigma / (2 * root_t)) - r * K * math.exp(-r * T) * norm_cdf(d2)
        else:
            delta = norm_cdf(d1) - 1.0
            theta_annual = -(S * norm_pdf(d1) * sigma / (2 * root_t)) + r * K * math.exp(-r * T) * norm_cdf(-d2)

        return {
            "delta": delta,
            "gamma": gamma,
            "theta": theta_annual / 365.0,
            "vega": vega,
        }
