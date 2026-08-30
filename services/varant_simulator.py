import math
from typing import Dict, Any, List
import pandas as pd
import numpy as np

# BIST Popüler İhraççı Varant Listesi & Dayanak Eşleştirme Bilgileri
# BIST Popüler İhraççı Varant Listesi & Dayanak Eşleştirme Bilgileri (İş Yatırım, Ahlatcı Yatırım, Ak Yatırım, Garanti)
BIST_WARRANT_DATABASE = {
    "THYAO": [
        # Ahlatcı Yatırım Varantları
        {"code": "THAHC", "type": "CALL", "strike": 320.0, "maturity_days": 45, "issue_price": 1.14, "spread": 0.01, "issuer": "Ahlatcı Yatırım", "delta": 0.62, "gearing": 6.8, "theta": -0.015, "status": "ALTIN"},
        {"code": "THAHD", "type": "CALL", "strike": 340.0, "maturity_days": 45, "issue_price": 0.67, "spread": 0.01, "issuer": "Ahlatcı Yatırım", "delta": 0.48, "gearing": 8.4, "theta": -0.018, "status": "ALTIN"},
        {"code": "THAHP", "type": "PUT",  "strike": 300.0, "maturity_days": 45, "issue_price": 0.84, "spread": 0.02, "issuer": "Ahlatcı Yatırım", "delta": -0.42, "gearing": 7.2, "theta": -0.014, "status": "KORUMA"},
        # İş Yatırım
        {"code": "THIAD", "type": "CALL", "strike": 320.0, "maturity_days": 45, "issue_price": 1.15, "spread": 0.01, "issuer": "İş Yatırım", "delta": 0.62, "gearing": 6.8, "theta": -0.015, "status": "ALTIN"},
        {"code": "THIAE", "type": "CALL", "strike": 340.0, "maturity_days": 45, "issue_price": 0.68, "spread": 0.01, "issuer": "İş Yatırım", "delta": 0.48, "gearing": 8.4, "theta": -0.018, "status": "ALTIN"},
        {"code": "THIPR", "type": "PUT",  "strike": 300.0, "maturity_days": 45, "issue_price": 0.85, "spread": 0.02, "issuer": "İş Yatırım", "delta": -0.42, "gearing": 7.2, "theta": -0.014, "status": "KORUMA"},
        # Ak Yatırım & Garanti
        {"code": "THAKC", "type": "CALL", "strike": 330.0, "maturity_days": 40, "issue_price": 0.88, "spread": 0.01, "issuer": "Ak Yatırım", "delta": 0.55, "gearing": 7.5, "theta": -0.016, "status": "ALTIN"}
    ],
    "AKBNK": [
        {"code": "AKAHC", "type": "CALL", "strike": 60.0, "maturity_days": 40, "issue_price": 0.44, "spread": 0.01, "issuer": "Ahlatcı Yatırım", "delta": 0.58, "gearing": 6.2, "theta": -0.008, "status": "ALTIN"},
        {"code": "AKAHD", "type": "CALL", "strike": 65.0, "maturity_days": 40, "issue_price": 0.27, "spread": 0.01, "issuer": "Ahlatcı Yatırım", "delta": 0.42, "gearing": 7.8, "theta": -0.010, "status": "ALTIN"},
        {"code": "AKIAD", "type": "CALL", "strike": 60.0, "maturity_days": 40, "issue_price": 0.45, "spread": 0.01, "issuer": "İş Yatırım", "delta": 0.58, "gearing": 6.2, "theta": -0.008, "status": "ALTIN"},
        {"code": "AKIAE", "type": "CALL", "strike": 65.0, "maturity_days": 40, "issue_price": 0.28, "spread": 0.01, "issuer": "İş Yatırım", "delta": 0.42, "gearing": 7.8, "theta": -0.010, "status": "ALTIN"}
    ],
    "GARAN": [
        {"code": "GAAHC", "type": "CALL", "strike": 120.0, "maturity_days": 42, "issue_price": 1.18, "spread": 0.01, "issuer": "Ahlatcı Yatırım", "delta": 0.60, "gearing": 5.9, "theta": -0.016, "status": "ALTIN"},
        {"code": "GAIAD", "type": "CALL", "strike": 120.0, "maturity_days": 42, "issue_price": 1.20, "spread": 0.01, "issuer": "Garanti", "delta": 0.60, "gearing": 5.9, "theta": -0.016, "status": "ALTIN"},
        {"code": "GAIAE", "type": "CALL", "strike": 130.0, "maturity_days": 42, "issue_price": 0.72, "spread": 0.01, "issuer": "Garanti", "delta": 0.46, "gearing": 7.5, "theta": -0.019, "status": "ALTIN"}
    ],
    "ISCTR": [
        {"code": "ISAHC", "type": "CALL", "strike": 15.0, "maturity_days": 45, "issue_price": 0.24, "spread": 0.01, "issuer": "Ahlatcı Yatırım", "delta": 0.64, "gearing": 6.5, "theta": -0.004, "status": "ALTIN"},
        {"code": "ISIAD", "type": "CALL", "strike": 15.0, "maturity_days": 45, "issue_price": 0.25, "spread": 0.01, "issuer": "İş Yatırım", "delta": 0.64, "gearing": 6.5, "theta": -0.004, "status": "ALTIN"}
    ],
    "YKBNK": [
        {"code": "YKAHC", "type": "CALL", "strike": 32.0, "maturity_days": 38, "issue_price": 0.51, "spread": 0.01, "issuer": "Ahlatcı Yatırım", "delta": 0.56, "gearing": 6.4, "theta": -0.009, "status": "ALTIN"},
        {"code": "YKIAD", "type": "CALL", "strike": 32.0, "maturity_days": 38, "issue_price": 0.52, "spread": 0.01, "issuer": "Ak Yatırım", "delta": 0.56, "gearing": 6.4, "theta": -0.009, "status": "ALTIN"}
    ],
    "EREGL": [
        {"code": "ERAHC", "type": "CALL", "strike": 52.0, "maturity_days": 50, "issue_price": 0.86, "spread": 0.01, "issuer": "Ahlatcı Yatırım", "delta": 0.55, "gearing": 5.5, "theta": -0.012, "status": "ALTIN"},
        {"code": "ERIAD", "type": "CALL", "strike": 52.0, "maturity_days": 50, "issue_price": 0.88, "spread": 0.01, "issuer": "İş Yatırım", "delta": 0.55, "gearing": 5.5, "theta": -0.012, "status": "ALTIN"}
    ],
    "TUPRS": [
        {"code": "TPAHC", "type": "CALL", "strike": 180.0, "maturity_days": 45, "issue_price": 1.42, "spread": 0.01, "issuer": "Ahlatcı Yatırım", "delta": 0.65, "gearing": 7.0, "theta": -0.020, "status": "ALTIN"},
        {"code": "TPIAD", "type": "CALL", "strike": 180.0, "maturity_days": 45, "issue_price": 1.45, "spread": 0.01, "issuer": "İş Yatırım", "delta": 0.65, "gearing": 7.0, "theta": -0.020, "status": "ALTIN"}
    ],
    "ASELS": [
        {"code": "ASAHC", "type": "CALL", "strike": 65.0, "maturity_days": 48, "issue_price": 0.74, "spread": 0.01, "issuer": "Ahlatcı Yatırım", "delta": 0.59, "gearing": 6.3, "theta": -0.011, "status": "ALTIN"},
        {"code": "ASIAD", "type": "CALL", "strike": 65.0, "maturity_days": 48, "issue_price": 0.76, "spread": 0.01, "issuer": "İş Yatırım", "delta": 0.59, "gearing": 6.3, "theta": -0.011, "status": "ALTIN"}
    ],
    "KCHOL": [
        {"code": "KCAHC", "type": "CALL", "strike": 220.0, "maturity_days": 45, "issue_price": 1.58, "spread": 0.02, "issuer": "Ahlatcı Yatırım", "delta": 0.58, "gearing": 6.0, "theta": -0.022, "status": "ALTIN"},
        {"code": "KCIAD", "type": "CALL", "strike": 220.0, "maturity_days": 45, "issue_price": 1.60, "spread": 0.02, "issuer": "İş Yatırım", "delta": 0.58, "gearing": 6.0, "theta": -0.022, "status": "ALTIN"}
    ],
    "SAHOL": [
        {"code": "SAAHC", "type": "CALL", "strike": 95.0, "maturity_days": 45, "issue_price": 0.80, "spread": 0.01, "issuer": "Ahlatcı Yatırım", "delta": 0.57, "gearing": 5.8, "theta": -0.012, "status": "ALTIN"},
        {"code": "SAIAD", "type": "CALL", "strike": 95.0, "maturity_days": 45, "issue_price": 0.82, "spread": 0.01, "issuer": "Ak Yatırım", "delta": 0.57, "gearing": 5.8, "theta": -0.012, "status": "ALTIN"}
    ],
    "SISE": [
        {"code": "SIAHC", "type": "CALL", "strike": 50.0, "maturity_days": 45, "issue_price": 0.43, "spread": 0.01, "issuer": "Ahlatcı Yatırım", "delta": 0.54, "gearing": 5.4, "theta": -0.007, "status": "ALTIN"},
        {"code": "SIIAD", "type": "CALL", "strike": 50.0, "maturity_days": 45, "issue_price": 0.44, "spread": 0.01, "issuer": "İş Yatırım", "delta": 0.54, "gearing": 5.4, "theta": -0.007, "status": "ALTIN"}
    ],
    "PGSUS": [
        {"code": "PGAHC", "type": "CALL", "strike": 250.0, "maturity_days": 40, "issue_price": 1.88, "spread": 0.02, "issuer": "Ahlatcı Yatırım", "delta": 0.68, "gearing": 7.2, "theta": -0.030, "status": "ALTIN"},
        {"code": "PGIAD", "type": "CALL", "strike": 250.0, "maturity_days": 40, "issue_price": 1.90, "spread": 0.02, "issuer": "İş Yatırım", "delta": 0.68, "gearing": 7.2, "theta": -0.030, "status": "ALTIN"}
    ],
    "BIMAS": [
        {"code": "BIAHC", "type": "CALL", "strike": 520.0, "maturity_days": 45, "issue_price": 3.35, "spread": 0.03, "issuer": "Ahlatcı Yatırım", "delta": 0.56, "gearing": 5.7, "theta": -0.045, "status": "ALTIN"},
        {"code": "BIIAD", "type": "CALL", "strike": 520.0, "maturity_days": 45, "issue_price": 3.40, "spread": 0.03, "issuer": "İş Yatırım", "delta": 0.56, "gearing": 5.7, "theta": -0.045, "status": "ALTIN"}
    ],
    "EKGYO": [
        {"code": "EKAHC", "type": "CALL", "strike": 12.0, "maturity_days": 35, "issue_price": 0.17, "spread": 0.01, "issuer": "Ahlatcı Yatırım", "delta": 0.62, "gearing": 6.9, "theta": -0.003, "status": "ALTIN"},
        {"code": "EKIAD", "type": "CALL", "strike": 12.0, "maturity_days": 35, "issue_price": 0.18, "spread": 0.01, "issuer": "İş Yatırım", "delta": 0.62, "gearing": 6.9, "theta": -0.003, "status": "ALTIN"}
    ]
}

class VarantSimulator:
    """
    VarantRadar Pro V7 - Black-Scholes & Greeks Varant Simülatörü
    Dayanak hissenin spot fiyatına, hedef seviyesine ve vadeye göre 
    varantın kuruş bazlı teorik değerini ve kâr/zarar potansiyelini hesaplar.
    """

    @staticmethod
    def calculate_greeks(spot_price: float, strike_price: float, days_to_maturity: int, 
                         volatility: float = 0.35, risk_free_rate: float = 0.45, 
                         warrant_type: str = "CALL", conversion_ratio: float = 1.0) -> Dict[str, float]:
        """
        Black-Scholes Modeli ile Delta, Gamma, Theta, Vega ve Teorik Fiyatı hesaplar.
        """
        try:
            if days_to_maturity <= 0 or spot_price <= 0 or strike_price <= 0:
                return {"price": 0.0, "delta": 0.0, "gamma": 0.0, "theta": 0.0, "vega": 0.0}

            T = days_to_maturity / 365.0
            r = risk_free_rate
            sigma = max(0.05, volatility)
            S = spot_price
            K = strike_price

            d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
            d2 = d1 - sigma * math.sqrt(T)

            # Cumulative standard normal distribution
            from scipy.stats import norm
            N_d1 = norm.cdf(d1)
            N_d2 = norm.cdf(d2)
            n_d1 = norm.pdf(d1)

            if warrant_type.upper() == "CALL":
                theoretical_price = (S * N_d1 - K * math.exp(-r * T) * N_d2) * conversion_ratio
                delta = N_d1 * conversion_ratio
                theta = (-(S * n_d1 * sigma) / (2 * math.sqrt(T)) - r * K * math.exp(-r * T) * N_d2) / 365.0 * conversion_ratio
            else: # PUT
                theoretical_price = (K * math.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)) * conversion_ratio
                delta = (N_d1 - 1.0) * conversion_ratio
                theta = (-(S * n_d1 * sigma) / (2 * math.sqrt(T)) + r * K * math.exp(-r * T) * norm.cdf(-d2)) / 365.0 * conversion_ratio

            gamma = (n_d1 / (S * sigma * math.sqrt(T))) * conversion_ratio
            vega = (S * math.sqrt(T) * n_d1) / 100.0 * conversion_ratio
            gearing = (S / max(0.01, theoretical_price)) * abs(delta)

            return {
                "theoretical_price": round(max(0.01, theoretical_price), 2),
                "delta": round(delta, 2),
                "gamma": round(gamma, 4),
                "theta": round(theta, 4),
                "vega": round(vega, 4),
                "gearing": round(gearing, 1)
            }
        except Exception:
            # Scipy fallback (basit yaklaşık matematik)
            approx_intrinsic = max(0.0, spot_price - strike_price) if warrant_type.upper() == "CALL" else max(0.0, strike_price - spot_price)
            time_value = spot_price * 0.04 * math.sqrt(max(1, days_to_maturity) / 365.0)
            theo = (approx_intrinsic + time_value) * conversion_ratio
            delta = 0.55 if warrant_type.upper() == "CALL" else -0.45
            return {
                "theoretical_price": round(max(0.01, theo), 2),
                "delta": delta,
                "gamma": 0.02,
                "theta": -0.015,
                "vega": 0.05,
                "gearing": 6.0
            }

    @classmethod
    def get_warrants_for_symbol(cls, symbol: str, current_price: float, target_price: float = None, issuer: str = "ALL") -> List[Dict[str, Any]]:
        """Dayanak hisse için uygun varantları ve hedef fiyattaki kâr simülasyonunu döndürür.
        Canlı Black-Scholes hesaplaması ile Greeks güncellenir."""
        clean_sym = symbol.replace(".IS", "").upper()
        warrants = BIST_WARRANT_DATABASE.get(clean_sym, [])
        
        if issuer and issuer != "ALL":
            issuer_clean = issuer.lower().strip()
            warrants = [w for w in warrants if issuer_clean in w.get("issuer", "").lower()]

        if not target_price or target_price <= 0:
            target_price = current_price * 1.099 # Varsayılan: Tavan (%9.9)

        results = []
        for w in warrants:
            issue_p = w.get("issue_price", 1.0)
            strike = w.get("strike", current_price)
            maturity = w.get("maturity_days", 45)
            wtype = w.get("type", "CALL")
            
            # 🛡️ VARANT VADE KALKANI (THETA SHIELD)
            # Vadesine 20 günden az kalmış varantlar zaman değeri (Time Decay) yüzünden aşırı risklidir.
            # Sistem bu varantları "Çöp Varant" olarak sınıflandırır ve kesinlikle önermez!
            if maturity < 20:
                continue
            
            # Canlı Black-Scholes Greeks hesaplaması (statik değil!)
            greeks = cls.calculate_greeks(
                spot_price=current_price,
                strike_price=strike,
                days_to_maturity=maturity,
                warrant_type=wtype
            )
            
            delta = greeks.get("delta", w.get("delta", 0.55))
            gearing = greeks.get("gearing", w.get("gearing", 6.0))
            theta_daily = greeks.get("theta", w.get("theta", -0.015))
            theo_price = greeks.get("theoretical_price", issue_p)
            
            # Hedef fiyattaki tahmini varant fiyatı: Delta * (Hedef - Mevcut) + Mevcut Varant Fiyatı
            spot_diff = target_price - current_price
            warrant_delta_gain = spot_diff * abs(delta)
            target_warrant_price = round(max(0.01, theo_price + warrant_delta_gain), 2)
            
            warrant_gain_pct = round(((target_warrant_price - theo_price) / theo_price) * 100, 1) if theo_price > 0 else 0
            spot_gain_pct = round(((target_price - current_price) / current_price) * 100, 1) if current_price > 0 else 0
            
            # Break-even (Başabaş) Fiyatı
            break_even = round(strike + (theo_price / abs(delta if delta != 0 else 0.5)), 2)
            
            # Hafta sonu zaman erimesi kaybı (2 günlük Theta)
            weekend_theta_loss = round(abs(theta_daily) * 2, 3)
            weekend_loss_pct = round((weekend_theta_loss / theo_price) * 100, 1) if theo_price > 0 else 0

            # Güvenlik & Risk Değerlendirmesi
            risk_badge = "DÜŞÜK RİSK"
            if maturity < 15:
                risk_badge = "YÜKSEK VADE RİSKİ (Çöp Olma Riski)"
            elif w.get("spread", 0.01) > 0.02:
                risk_badge = "MAKAS RİSKİ (İhraççı Makası Geniş)"
            elif abs(delta) < 0.30:
                risk_badge = "UZAK KULLANIM FİYATI (OTM)"

            results.append({
                "code": w.get("code"),
                "type": wtype,
                "issuer": w.get("issuer"),
                "strike": strike,
                "maturity_days": maturity,
                "current_warrant_price": f"₺{theo_price:.2f}",
                "target_warrant_price": f"₺{target_warrant_price:.2f}",
                "warrant_gain_pct": f"+%{warrant_gain_pct}",
                "spot_gain_pct": f"+%{spot_gain_pct}",
                "gearing": f"{gearing}x",
                "delta": round(delta, 2),
                "theta": f"{round(theta_daily, 4)} TL/gün",
                "weekend_decay": f"-{weekend_theta_loss} TL (%{weekend_loss_pct})",
                "break_even": f"₺{break_even}",
                "spread": f"₺{w.get('spread', 0.01):.2f}",
                "risk_badge": risk_badge,
                "status": w.get("status", "ALTIN")
            })

        return results
