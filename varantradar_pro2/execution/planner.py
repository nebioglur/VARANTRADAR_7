from typing import Dict, Any

class TradePlanner:
    """
    CFG-06 Trade Planner (İşlem Planlayıcısı)
    AI karar motoru "AL" dedikten sonra "Nereden, Nasıl, Nereye Kadar?" 
    sorularına yanıt olacak icra planını çizer.
    """
    
    @staticmethod
    def generate_trade_plan(
        symbol: str, 
        current_price: float, 
        atr: float, 
        trend_status: str,
        vix_level: float = 20.0
    ) -> Dict[str, Any]:
        """
        Mevcut fiyat, VIX ve ATR'ye göre kademeli giriş,
        dinamik zarar kes ve kâr alma seviyelerini belirler.
        """
        
        import math
        
        # Güvenlik Kontrolleri (NaN / Null Safe Guard)
        if math.isnan(atr) or atr <= 0:
            atr = current_price * 0.02  # Varsayılan %2 volatilite
        if math.isnan(current_price) or current_price <= 0:
            return {"Error": "Geçersiz fiyat verisi."}
            
        # 1. Kademeli Giriş (Scaling In) - Volatiliteye (VIX) Duyarlı
        # VIX yüksekse fiyat dalgalanması çok olur, kademeler açılmalıdır.
        volatility_factor = 1.5 if vix_level > 25.0 else (0.5 if vix_level < 15.0 else 1.0)
        
        entry_1 = round(current_price, 2)
        entry_2 = round(current_price - (atr * volatility_factor), 2)
        entry_3 = round(current_price - (atr * volatility_factor * 2.0), 2)
        avg_entry = round((entry_1 + entry_2 + entry_3) / 3, 2)
        
        # 2. Stop-Loss (Zarar Kes) Seviyesi (3 Kademe)
        stop_multiplier = 2.5 if trend_status == "GÜÇLÜ YÜKSELİŞ" else 1.5
        stop_1 = round(avg_entry - (atr * stop_multiplier * 0.5), 2)
        stop_2 = round(avg_entry - (atr * stop_multiplier * 1.0), 2)
        stop_3 = round(avg_entry - (atr * stop_multiplier * 1.5), 2)
        
        # 3. Take-Profit (Kâr Alma) Hedefleri (3 Kademe)
        tp1 = round(avg_entry + (atr * 2.0), 2)
        tp2 = round(avg_entry + (atr * 4.0), 2)
        tp3 = round(avg_entry + (atr * 7.0), 2)
        
        # 4. Destek ve Dirençler (ATR Bazlı Pseudo-Pivotlar)
        s1 = round(current_price - (atr * 1.2), 2)
        s2 = round(current_price - (atr * 2.4), 2)
        s3 = round(current_price - (atr * 3.6), 2)
        sub_s1 = round(current_price - (atr * 5.0), 2)
        sub_s2 = round(current_price - (atr * 6.5), 2)
        sub_s3 = round(current_price - (atr * 8.0), 2)
        
        r1 = round(current_price + (atr * 1.2), 2)
        r2 = round(current_price + (atr * 2.4), 2)
        r3 = round(current_price + (atr * 3.6), 2)
        sup_r1 = round(current_price + (atr * 5.0), 2)
        sup_r2 = round(current_price + (atr * 6.5), 2)
        sup_r3 = round(current_price + (atr * 8.0), 2)
        
        # Risk / Getiri Hesaplaması (TP2 baz alınarak)
        risk = avg_entry - stop_2
        reward = tp2 - avg_entry
        risk_reward_ratio = round(reward / risk, 2) if risk > 0 else 0
        
        # Kural: Risk/Ödül oranı 2.0'nin altındaysa İŞLEMİ REDDET.
        status = "VALID" if risk_reward_ratio >= 2.0 else "INVALID_RISK_REWARD"
        
        return {
            "Symbol": symbol,
            "Current_Price": current_price,
            "Entry_Plan": {
                "Strategy": "Kademeli Alım (Scaling-In)",
                "Volatility_Factor": volatility_factor,
                "Entry_1": entry_1,
                "Entry_2": entry_2,
                "Entry_3": entry_3,
                "Average_Cost": avg_entry
            },
            "Exit_Plan": {
                "Take_Profit_1": tp1,
                "Take_Profit_2": tp2,
                "Take_Profit_3": tp3,
                "Stop_Loss_1": stop_1,
                "Stop_Loss_2": stop_2,
                "Stop_Loss_3": stop_3
            },
            "Support_Levels": {
                "S1": s1, "S2": s2, "S3": s3,
                "Sub_S1": sub_s1, "Sub_S2": sub_s2, "Sub_S3": sub_s3
            },
            "Resistance_Levels": {
                "R1": r1, "R2": r2, "R3": r3,
                "Sup_R1": sup_r1, "Sup_R2": sup_r2, "Sup_R3": sup_r3
            },
            "Dynamic_ATR": round(atr, 2),
            "Risk_Reward_Ratio": risk_reward_ratio,
            "Trade_Status": status
        }
