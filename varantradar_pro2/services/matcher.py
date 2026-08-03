import pandas as pd
from services.warrant_engine import WarrantEngine

class WarrantMatcher:
    """
    VarantRadar Pro V4 - Eşleştirme Motoru
    Hisse Sinyali (AL/SAT) ile piyasadaki en uygun varantı eşleştirir.
    """
    def __init__(self):
        self.engine = WarrantEngine()

    def find_best_warrant(self, symbol: str, action: str, current_price: float) -> dict:
        """
        Modül 8 & 9: Eşleştirme ve Sıralama
        En uygun 1 adet varantı döndürür (Geriye dönük uyumluluk için).
        """
        best_warrants_df = self.find_top_warrants(symbol, action, current_price, top_n=1)
        if best_warrants_df.empty:
            return None
        
        row = best_warrants_df.iloc[0]
        return {
            "warrant_code": row['warrant_code'],
            "strike_price": row['strike'],
            "maturity_date": row['maturity_date'],
            "days_to_maturity": row['days_to_maturity'],
            "delta": row['delta'],
            "theta": row['theta'],
            "gamma": row['gamma'],
            "vega": row['vega'],
            "multiplier": row['multiplier'],
            "match_score": row['Kalite_Puanı'],
            "bid": row['bid'],
            "ask": row['ask'],
            "eff_gearing": row['Etkin_Kaldirac']
        }

    def find_top_warrants(self, symbol: str, action: str, current_price: float, top_n: int = 5) -> pd.DataFrame:
        """
        Belirtilen yön (AL=CALL, SAT=PUT) için en yüksek puanlı N varantı döndürür.
        """
        if action not in ["AL", "SAT"]:
            return pd.DataFrame()
            
        warrant_type = "CALL" if action == "AL" else "PUT"
        
        # 1. Tüm Olası Varantları Çek/Üret
        raw_warrants_df = self.engine.generate_warrants_for_stock(symbol, current_price)
        
        # 2. Yön Filtresi (Sadece CALL veya sadece PUT)
        filtered_df = raw_warrants_df[raw_warrants_df['type'] == warrant_type].copy()
        
        # 3. Puanlama (Modül 7)
        scored_df = self.engine.evaluate_warrants(filtered_df, current_price)
        
        if scored_df.empty:
            return pd.DataFrame()
            
        # 4. Çöpleri Ele (Kalite Puanı 0 olanlar, son haftaya girmiş olanlar)
        clean_df = scored_df[(scored_df['Kalite_Puanı'] > 30) & (scored_df['days_to_maturity'] >= 7)].copy()
        
        if clean_df.empty:
            return pd.DataFrame()
            
        # 5. Sıralama (Puanı en yüksek olan en üstte)
        clean_df = clean_df.sort_values(by="Kalite_Puanı", ascending=False).reset_index(drop=True)
        
        return clean_df.head(top_n)

    def calculate_trade_plan(self, warrant_info: dict, stock_target: float, stock_stop: float, current_stock_price: float) -> dict:
        """
        Modül 10: Varant İşlem Planı
        Hisse hedefine giderse varant kaç para olur? Stop olursa kaç para olur? (Black-Scholes Projeksiyonu)
        """
        from services.warrant_math import WarrantMath
        
        w_type = "CALL" if warrant_info['delta'] > 0 else "PUT"
        T = warrant_info.get('days_to_maturity', 30) / 365.0
        strike = warrant_info.get('strike', warrant_info.get('strike_price', 0))
        mult = warrant_info.get('multiplier', 1.0)
        r = self.engine.risk_free_rate
        vol = self.engine.volatility
        
        # Target Price Projection
        if w_type == "CALL":
            target_raw = WarrantMath.black_scholes_call(stock_target, strike, T, r, vol)
            stop_raw = WarrantMath.black_scholes_call(stock_stop, strike, T, r, vol)
        else:
            target_raw = WarrantMath.black_scholes_put(stock_target, strike, T, r, vol)
            stop_raw = WarrantMath.black_scholes_put(stock_stop, strike, T, r, vol)
            
        target_price = round(target_raw * mult, 2)
        stop_price = round(stop_raw * mult, 2)
        entry_price = warrant_info['ask']
        
        profit_pct = ((target_price - entry_price) / entry_price * 100) if entry_price > 0 else 0
        loss_pct = ((stop_price - entry_price) / entry_price * 100) if entry_price > 0 else 0
        
        # AI Yorumu
        if profit_pct > abs(loss_pct) * 2:
            ai_note = "Risk/Getiri oranı muazzam (>2). İşleme girmek için teknik olarak mükemmel fırsat."
        elif profit_pct > abs(loss_pct):
            ai_note = "Risk/Getiri oranı pozitif (>1). İşlem yapılabilir ancak stop seviyesine katı şekilde uyulmalı."
        else:
            ai_note = "DİKKAT! Beklenen zarar, beklenen kazançtan daha büyük. Varant çok riskli, pas geçilmeli."
            
        return {
            "Entry": entry_price,
            "Target": target_price,
            "Stop": stop_price,
            "Profit_Pct": round(profit_pct, 2),
            "Loss_Pct": round(loss_pct, 2),
            "AI_Note": ai_note
        }
