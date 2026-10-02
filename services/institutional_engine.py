import pandas as pd
import numpy as np

class InstitutionalEngine:
    """
    VarantRadar Pro V10 - Institutional Edition
    Smart Money (Akıllı Para), Order Flow Simülasyonu ve Volume Profile hesaplamaları.
    """
    
    @staticmethod
    def calculate_volume_profile(df: pd.DataFrame, bins: int = 50) -> dict:
        """
        Modül 4: Market Profile (Volume Profile / POC / VAH / VAL)
        Fiyat aralıklarındaki hacim birikimini hesaplar.
        """
        if df.empty or 'volume' not in df.columns:
            return {"error": "Veri yetersiz"}
            
        min_price = df['low'].min()
        max_price = df['high'].max()
        price_bins = np.linspace(min_price, max_price, bins)
        
        # Hacmi fiyat aralığına dağıt (Basit simülasyon)
        volume_profile = np.zeros(bins - 1)
        
        for index, row in df.iterrows():
            typ_price = (row['high'] + row['low'] + row['close']) / 3
            # Hangi bine düştüğünü bul
            idx = np.digitize(typ_price, price_bins) - 1
            if 0 <= idx < len(volume_profile):
                volume_profile[idx] += row['volume']
                
        # POC (Point of Control) - En yüksek hacmin olduğu fiyat
        poc_idx = np.argmax(volume_profile)
        poc_price = (price_bins[poc_idx] + price_bins[poc_idx + 1]) / 2
        
        # Value Area (Toplam hacmin %70'inin döndüğü yer)
        total_volume = np.sum(volume_profile)
        value_area_volume = total_volume * 0.70
        
        # Expand from POC
        current_vol = volume_profile[poc_idx]
        up_idx = poc_idx + 1
        down_idx = poc_idx - 1
        
        while current_vol < value_area_volume and (up_idx < len(volume_profile) or down_idx >= 0):
            vol_up = volume_profile[up_idx] if up_idx < len(volume_profile) else 0
            vol_down = volume_profile[down_idx] if down_idx >= 0 else 0
            
            if vol_up > vol_down:
                current_vol += vol_up
                up_idx += 1
            else:
                current_vol += vol_down
                down_idx -= 1
                
        vah = price_bins[min(up_idx, len(price_bins)-1)]
        val = price_bins[max(down_idx, 0)]
        
        return {
            "POC": poc_price,
            "VAH": vah,
            "VAL": val,
            "profile_bins": price_bins.tolist(),
            "profile_vols": volume_profile.tolist()
        }

    @staticmethod
    def detect_smart_money(df: pd.DataFrame) -> dict:
        """
        Modül 2 & 3: Smart Money ve Order Flow Emilim (Absorption) Tespiti
        Uzun fitiller, yüksek hacim ve fiyatın ilerleyememesi (Absorption) aranır.
        """
        if df.empty or len(df) < 5:
            return {"status": "Yetersiz Veri", "score": 0}
            
        recent = df.tail(5)
        avg_vol = df['volume'].mean()
        
        bullish_absorption = False
        bearish_absorption = False
        smart_money_score = 50
        note = "Stabil likidite."
        
        for idx, row in recent.iterrows():
            body = abs(row['close'] - row['open'])
            range_total = row['high'] - row['low']
            
            if range_total == 0: continue
            
            lower_wick = min(row['open'], row['close']) - row['low']
            upper_wick = row['high'] - max(row['open'], row['close'])
            
            is_high_volume = row['volume'] > (avg_vol * 1.5)
            
            # Kurumsal Alım (Stop Avı / Emilim) -> Fiyat düşüyor ama dev hacimle aşağıdan topluyorlar
            if is_high_volume and lower_wick > (range_total * 0.5) and body < (range_total * 0.3):
                bullish_absorption = True
                smart_money_score += 20
                note = "Kurumsal Alım Tespiti (Bullish Absorption & Stop Hunting): Aşağı yönlü likidite temizlendi, akıllı para topluyor."
                
            # Kurumsal Satış (Mal Çıkma)
            if is_high_volume and upper_wick > (range_total * 0.5) and body < (range_total * 0.3):
                bearish_absorption = True
                smart_money_score -= 20
                note = "Kurumsal Satış Tespiti (Bearish Absorption): Yukarı yönlü ataklar yüksek hacimle satılıyor (Mal Çıkma)."
                
        smart_money_score = max(0, min(100, smart_money_score))
        
        return {
            "Score": smart_money_score,
            "Note": note,
            "Bullish_Absorption": bullish_absorption,
            "Bearish_Absorption": bearish_absorption
        }
