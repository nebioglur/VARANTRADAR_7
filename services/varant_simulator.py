import math
import unicodedata
from typing import Dict, Any, List
from datetime import datetime

from services.warrant_math import WarrantMath


def _norm_tr(s: str) -> str:
    """Turkce karakterleri ICEREN metinleri karsilastirma icin normalize eder."""
    s = unicodedata.normalize("NFKD", str(s).lower())
    return "".join(c for c in s if not unicodedata.combining(c))

# Gerçek BIST ihraççıları ve varant kodu harf kalıpları
WARRANT_ISSUERS = [
    {"name": "İş Yatırım", "letter": "I", "vol": 0.38},
    {"name": "Ahlatcı Yatırım", "letter": "A", "vol": 0.42},
    {"name": "Ak Yatırım", "letter": "K", "vol": 0.40},
    {"name": "Garanti BBVA", "letter": "G", "vol": 0.39},
    {"name": "Yapı Kredi", "letter": "Y", "vol": 0.41},
]

RISK_FREE_RATE = 0.45  # TR faiz ortamı
MULTIPLIER = 0.1       # BIST varantlarının tipik çarpanı


class VarantSimulator:
    """
    VarantRadar Pro - Black-Scholes tabanlı dinamik varant simülatörü.
    Dayanak hissenin GÜNCEL fiyatı üzerinden gerçekçi strike/vade/fiyat üretir;
    statik (bayat) strike verisi kullanmaz. Böylece hedef fiyattaki kâr/zarar
    hesabı her zaman güncel fiyatla tutarlıdır.
    """

    @staticmethod
    def calculate_greeks(spot_price: float, strike_price: float, days_to_maturity: int,
                         volatility: float = 0.35, risk_free_rate: float = 0.45,
                         warrant_type: str = "CALL", conversion_ratio: float = 1.0) -> Dict[str, float]:
        try:
            if days_to_maturity <= 0 or spot_price <= 0 or strike_price <= 0:
                return {"price": 0.0, "delta": 0.0, "gamma": 0.0, "theta": 0.0, "vega": 0.0}

            T = days_to_maturity / 365.0
            greeks = WarrantMath.calculate_greeks(spot_price, strike_price, T,
                                                  risk_free_rate, volatility, warrant_type)
            if warrant_type.upper() == "CALL":
                price = WarrantMath.black_scholes_call(spot_price, strike_price, T,
                                                       risk_free_rate, volatility)
            else:
                price = WarrantMath.black_scholes_put(spot_price, strike_price, T,
                                                      risk_free_rate, volatility)
            greeks["price"] = price * conversion_ratio
            return greeks
        except Exception:
            return {"price": 0.0, "delta": 0.0, "gamma": 0.0, "theta": 0.0, "vega": 0.0}

    @classmethod
    def get_warrants_for_symbol(cls, symbol: str, current_price: float,
                                target_price: float = None, issuer: str = "ALL") -> List[Dict[str, Any]]:
        """Dayanak hisse için güncel fiyata göre üretilmiş varantları ve hedef fiyat kâr simülasyonunu döndürür."""
        clean_sym = symbol.replace(".IS", "").upper()
        try:
            spot = float(current_price)
        except (TypeError, ValueError):
            return []
        if spot <= 0:
            return []

        if not target_price or target_price <= 0:
            target_price = spot * 1.099  # Varsayılan: Tavan (%9.9)
        target_price = float(target_price)

        # İhraççı filtresi (Turkce karakter duyarsiz)
        selected_issuers = WARRANT_ISSUERS
        if issuer and str(issuer).upper() != "ALL":
            issuer_clean = _norm_tr(issuer).strip()
            selected_issuers = [i for i in WARRANT_ISSUERS if issuer_clean in _norm_tr(i["name"])]

        # Gerçekçi vade ve strike merdiveni
        maturities = [30, 60, 90, 180]
        call_strike_multipliers = [0.95, 1.00, 1.05, 1.10]  # ITM -> OTM
        put_strike_multipliers = [0.95, 1.00]

        results = []
        for mat_idx, days in enumerate(maturities):
            T = days / 365.0

            for iss_idx, iss in enumerate(selected_issuers):
                sigma = iss["vol"]

                # CALL'lar (tavan hedefi senaryosunun ana ürünü)
                for st_idx, mult in enumerate(call_strike_multipliers):
                    strike = round(spot * mult, 2)
                    w = cls._build_warrant(
                        clean_sym, iss, "CALL", "C", spot, strike, T, days,
                        target_price, sigma, MULTIPLIER,
                        code=f"{clean_sym[:2]}{iss['letter']}{mat_idx}{st_idx}")
                    results.append(w)

                # PUT'lar (korum senaryosu) - sadece 1 vade x 2 strike
                if mat_idx in (0, 1):
                    for st_idx, mult in enumerate(put_strike_multipliers):
                        strike = round(spot * mult, 2)
                        w = cls._build_warrant(
                            clean_sym, iss, "PUT", "P", spot, strike, T, days,
                            target_price, sigma, MULTIPLIER,
                            code=f"{clean_sym[:2]}{iss['letter']}{mat_idx}{st_idx}")
                        results.append(w)

        # Sıralama: kısa vade ve yakın strike; CALL/PUT dengeli (32 CALL + 8 PUT)
        results = [w for w in results if w]
        calls = sorted([w for w in results if w["type"] == "CALL"],
                       key=lambda w: (w["maturity_days"], w["strike"]))
        puts = sorted([w for w in results if w["type"] == "PUT"],
                      key=lambda w: (w["maturity_days"], w["strike"]))
        return (calls[:32] + puts[:8])

    @classmethod
    def _build_warrant(cls, clean_sym, issuer, wtype, type_letter, spot, strike,
                       T, days, target_price, sigma, multiplier, code):
        try:
            if wtype == "CALL":
                price_now = WarrantMath.black_scholes_call(spot, strike, T, RISK_FREE_RATE, sigma)
                price_tgt = WarrantMath.black_scholes_call(target_price, strike, T, RISK_FREE_RATE, sigma)
            else:
                price_now = WarrantMath.black_scholes_put(spot, strike, T, RISK_FREE_RATE, sigma)
                price_tgt = WarrantMath.black_scholes_put(target_price, strike, T, RISK_FREE_RATE, sigma)

            greeks = WarrantMath.calculate_greeks(spot, strike, T, RISK_FREE_RATE, sigma, wtype)

            # Varant fiyatı (kuruş hassasiyetli, minimum tick)
            wp_now = max(0.01, round(price_now * multiplier, 2))
            wp_tgt = max(0.01, round(price_tgt * multiplier, 2))

            gain_pct = round(((wp_tgt - wp_now) / wp_now) * 100, 1) if wp_now > 0 else 0.0
            spot_gain_pct = round(((target_price - spot) / spot) * 100, 1) if spot > 0 else 0.0

            # Etkin kaldıraç
            delta = float(greeks.get("delta", 0) or 0)
            eff_gearing = round((spot / wp_now) * multiplier * abs(delta), 1) if wp_now > 0 else 0.0

            # Theta (günlük TL kaybı, varant başına)
            theta_daily = float(greeks.get("theta", 0) or 0) * multiplier
            weekend_loss = round(abs(theta_daily) * 2, 3)
            weekend_loss_pct = round((weekend_loss / wp_now) * 100, 1) if wp_now > 0 else 0.0

            # Başabaş (CALL: strike + fiyat/çarpan; PUT: strike - fiyat/çarpan)
            if wtype == "CALL":
                break_even = round(strike + (wp_now / multiplier), 2)
            else:
                break_even = round(strike - (wp_now / multiplier), 2)

            # Piyasa yapıcı makası (fiyatın ~%2'si, min 1 kuruş)
            spread = max(0.01, round(wp_now * 0.02, 2))

            # Risk etiketi
            risk_badge = "DÜŞÜK RİSK"
            if days < 20:
                risk_badge = "YÜKSEK VADE RİSKİ (Çöp Olma Riski)"
            elif abs(delta) < 0.25:
                risk_badge = "UZAK KULLANIM FİYATI (OTM)"
            elif (spread / wp_now * 100) > 4:
                risk_badge = "MAKAS RİSKİ (İhraççı Makası Geniş)"

            sign = "+" if gain_pct >= 0 else "-"
            spot_sign = "+" if spot_gain_pct >= 0 else "-"

            return {
                "code": code,
                "type": wtype,
                "issuer": issuer["name"],
                "strike": strike,
                "maturity_days": days,
                "maturity_date": datetime.fromordinal(datetime.now().toordinal() + days).strftime("%Y-%m-%d"),
                "current_warrant_price": f"₺{wp_now:.2f}",
                "target_warrant_price": f"₺{wp_tgt:.2f}",
                "warrant_gain_pct": f"{sign}%{abs(gain_pct)}",
                "spot_gain_pct": f"{spot_sign}%{abs(spot_gain_pct)}",
                "gearing": f"{eff_gearing}x",
                "delta": round(delta, 2),
                "theta": f"{theta_daily:.3f} TL/gün",
                "weekend_decay": f"-{weekend_loss} TL (%{weekend_loss_pct})",
                "break_even": f"₺{break_even}",
                "spread": f"₺{spread:.2f}",
                "risk_badge": risk_badge,
                "status": "ALTIN"
            }
        except Exception:
            return None
