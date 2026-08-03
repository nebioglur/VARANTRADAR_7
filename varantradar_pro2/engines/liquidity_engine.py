import pandas as pd
import numpy as np
from typing import Dict, Any

class LiquidityEngine:
    """
    Portföydeki pozisyonların nakde dönüştürülme hızını (Days to Liquidate),
    büyük emirlerin tahtada yaratacağı fiyat kaymasını (Slippage/Market Impact) 
    ve genel likidite skorunu hesaplar.
    """
    
    @staticmethod
    def calculate_liquidation_metrics(df: pd.DataFrame, position_size_cash: float, max_volume_participation_pct: float = 0.10) -> Dict[str, Any]:
        """
        df: Hissenin geçmiş OHLCV verisi (En az 30 günlük önerilir).
        position_size_cash: Kapatılmak istenen pozisyonun TL cinsinden büyüklüğü.
        max_volume_participation_pct: Günlük hacmin maksimum yüzde kaçının alınabileceği/satılabileceği varsayımı. (Örn: %10)
        """
        if df.empty or 'volume' not in df.columns or len(df) < 20:
            return {"error": "Likidite analizi için yeterli hacim verisi (min 20 gün) bulunamadı."}
            
        # Son 20 günlük Ortalama İşlem Hacmi (ADV - Average Daily Volume) - Adet bazında
        adv_shares = df['volume'].tail(20).mean()
        current_price = df['close'].iloc[-1]
        
        adv_cash = adv_shares * current_price
        
        if adv_cash == 0:
            return {"error": "Hacim 0."}
            
        # Maksimum günlük likidite kapasitesi
        daily_liquidity_capacity = adv_cash * max_volume_participation_pct
        
        # Days to Liquidate (Pozisyonu kapatmak kaç gün sürer?)
        days_to_liquidate = position_size_cash / daily_liquidity_capacity if daily_liquidity_capacity > 0 else float('inf')
        
        # Piyasa Etkisi (Market Impact / Slippage Estimate) - Basit bir karekök modeli (Amihud benzeri)
        # Slippage = c * volatility * sqrt(OrderSize / ADV)
        # c = Sabit katsayı (Genelde 0.1 - 0.5 arası)
        volatility = df['close'].pct_change().std()
        
        # Pozisyon büyüklüğünün hacme oranı
        participation_rate = position_size_cash / adv_cash
        
        # Eğer hacmin %1'inden az ise slippage sıfıra yakın varsayılır.
        c = 0.1 
        estimated_slippage_pct = c * volatility * np.sqrt(participation_rate) if participation_rate > 0 else 0
        estimated_slippage_cost = position_size_cash * estimated_slippage_pct
        
        # Likidite Skoru (100 üzerinden - Yüksek olması iyi)
        # Günlük hacim / Pozisyon büyüklüğü > 100 ise skor 100, azaldıkça düşer.
        liquidity_ratio = adv_cash / position_size_cash if position_size_cash > 0 else 1000
        liquidity_score = min(100.0, max(0.0, liquidity_ratio)) # Basit capping
        
        return {
            "Average_Daily_Volume_Cash": round(adv_cash, 2),
            "Days_to_Liquidate": round(days_to_liquidate, 2),
            "Estimated_Slippage_Pct": round(estimated_slippage_pct * 100, 4),
            "Estimated_Slippage_Cost": round(estimated_slippage_cost, 2),
            "Liquidity_Score": round(liquidity_score, 2),
            "Warning": "HIGH_LIQUIDITY_RISK" if days_to_liquidate > 1 else "SAFE"
        }
