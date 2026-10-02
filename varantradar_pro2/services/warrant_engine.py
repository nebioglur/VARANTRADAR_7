import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from services.warrant_math import WarrantMath
import math

class WarrantEngine:
    """
    VarantRadar Pro V4 - Varant Motoru
    BIST Varantlarının simüle edilmesi, Greeks ve Fiyatlama analizleri.
    """
    def __init__(self):
        self.risk_free_rate = 0.45 # Türkiye CDS ve faiz ortamına göre %45 risksiz faiz
        self.volatility = 0.40 # Ortalama tarihsel volatilite (%40)
    
    def generate_warrants_for_stock(self, symbol: str, current_price: float) -> pd.DataFrame:
        """
        Gerçek API olmadığı için, hissenin güncel fiyatı üzerinden
        gerçekçi (ITM, ATM, OTM) Alım ve Satım varantları üretir. (Modül 1 & 2)
        """
        warrants = []
        base_code = symbol.replace(".IS", "")[:2] # ISCTR -> IS
        
        # 3 Farklı Vade: Kısa (15 Gün), Orta (45 Gün), Uzun (90 Gün)
        maturities = [15, 45, 90]
        
        # 5 Farklı Strike (Kullanım Fiyatı): Derin OTM, OTM, ATM, ITM, Derin ITM
        # CALL için: %-10, %-5 (ITM), %0 (ATM), %+5, %+10 (OTM)
        strike_multipliers = [0.90, 0.95, 1.0, 1.05, 1.10]
        
        multiplier = 0.1 # Her varantın çarpanı genelde 0.1, 0.05 vs olur.
        
        for days in maturities:
            maturity_date = datetime.now() + timedelta(days=days)
            T = days / 365.0
            
            for m in strike_multipliers:
                strike = round(current_price * m, 2)
                
                # CALL Varantı Üret (Alım)
                call_price_raw = WarrantMath.black_scholes_call(current_price, strike, T, self.risk_free_rate, self.volatility)
                call_price = max(0.01, round(call_price_raw * multiplier, 2))
                
                # Gerçek piyasada MM (Piyasa Yapıcı) her zaman spread koyar
                call_spread = max(0.01, round(call_price * 0.02, 2))
                call_bid = call_price
                call_ask = round(call_price + call_spread, 2)
                
                # Greeks
                c_greeks = WarrantMath.calculate_greeks(current_price, strike, T, self.risk_free_rate, self.volatility, 'CALL')
                
                warrants.append({
                    'warrant_code': f"{base_code}I{np.random.choice(['A','B','C','D','E'])}",
                    'underlying': symbol,
                    'type': 'CALL',
                    'strike': strike,
                    'maturity_date': maturity_date.strftime("%Y-%m-%d"),
                    'days_to_maturity': days,
                    'multiplier': multiplier,
                    'bid': call_bid,
                    'ask': call_ask,
                    'spread_pct': round((call_ask - call_bid) / call_ask * 100, 2),
                    'delta': c_greeks['delta'],
                    'gamma': c_greeks['gamma'],
                    'theta': c_greeks['theta'],
                    'vega': c_greeks['vega']
                })
                
                # PUT Varantı Üret (Satım)
                put_price_raw = WarrantMath.black_scholes_put(current_price, strike, T, self.risk_free_rate, self.volatility)
                put_price = max(0.01, round(put_price_raw * multiplier, 2))
                put_spread = max(0.01, round(put_price * 0.02, 2))
                put_bid = put_price
                put_ask = round(put_price + put_spread, 2)
                
                p_greeks = WarrantMath.calculate_greeks(current_price, strike, T, self.risk_free_rate, self.volatility, 'PUT')
                
                warrants.append({
                    'warrant_code': f"{base_code}P{np.random.choice(['A','B','C','D','E'])}",
                    'underlying': symbol,
                    'type': 'PUT',
                    'strike': strike,
                    'maturity_date': maturity_date.strftime("%Y-%m-%d"),
                    'days_to_maturity': days,
                    'multiplier': multiplier,
                    'bid': put_bid,
                    'ask': put_ask,
                    'spread_pct': round((put_ask - put_bid) / put_ask * 100, 2),
                    'delta': p_greeks['delta'],
                    'gamma': p_greeks['gamma'],
                    'theta': p_greeks['theta'],
                    'vega': p_greeks['vega']
                })
                
        return pd.DataFrame(warrants)

    def evaluate_warrants(self, df: pd.DataFrame, underlying_price: float) -> pd.DataFrame:
        """
        Modül 4, 5, 6 ve 7: Fiyatlama, Kalite, Vade ve Toplam Puanlama Analizi
        """
        if df.empty:
            return df
            
        scores = []
        for _, row in df.iterrows():
            # 1. Delta Puanı (Max 30) - En uygun delta 0.40 - 0.60 arasıdır.
            delta_abs = abs(row['delta'])
            if 0.40 <= delta_abs <= 0.60: delta_score = 30
            elif 0.30 <= delta_abs <= 0.70: delta_score = 20
            elif 0.15 <= delta_abs <= 0.85: delta_score = 10
            else: delta_score = 0
            
            # 2. Theta (Zaman Değeri) Erimesi Puanı (Max 25) - Theta ne kadar az negatifse o kadar iyi.
            # Theta'nın fiyata oranına bakarız (Günlük erime yüzdesi)
            daily_decay_pct = abs(row['theta'] * row['multiplier']) / row['ask'] * 100 if row['ask'] > 0 else 100
            if daily_decay_pct < 1.0: theta_score = 25
            elif daily_decay_pct < 2.5: theta_score = 15
            elif daily_decay_pct < 5.0: theta_score = 5
            else: theta_score = -10 # Çöp varant cezası
            
            # 3. Vade Kalitesi Puanı (Max 20)
            if row['days_to_maturity'] > 60: vade_score = 20
            elif row['days_to_maturity'] > 30: vade_score = 15
            elif row['days_to_maturity'] > 15: vade_score = 5
            else: vade_score = -20 # Son 15 gün aşırı risklidir.
            
            # 4. Makas (Spread) ve Fiyat Puanı (Max 25)
            if row['spread_pct'] <= 2.0: spread_score = 25
            elif row['spread_pct'] <= 5.0: spread_score = 15
            elif row['spread_pct'] <= 10.0: spread_score = 5
            else: spread_score = 0
            
            total_score = delta_score + theta_score + vade_score + spread_score
            
            # Etkin Kaldıraç (Effective Gearing)
            # Etkin Kaldıraç = (Dayanak Fiyat / Varant Fiyatı) * Çarpan * Delta
            eff_gearing = (underlying_price / row['ask']) * row['multiplier'] * abs(row['delta']) if row['ask'] > 0 else 0
            
            scores.append({
                'Kalite_Puanı': max(0, min(100, total_score)),
                'Etkin_Kaldirac': round(eff_gearing, 2),
                'Gunluk_Erime_Yuzde': round(daily_decay_pct, 2)
            })
            
        scores_df = pd.DataFrame(scores)
        df_result = pd.concat([df.reset_index(drop=True), scores_df], axis=1)
        return df_result
