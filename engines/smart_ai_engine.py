import pandas as pd
import numpy as np
from typing import Dict, Any

class SmartAI_Engine:
    """
    CFG-07 Smart Money Final AI Motoru.
    Wyckoff Piyasa Döngülerini (Akümülasyon, Markup, Dağıtım, Markdown)
    ve Yapay Zeka Destekli Manipülasyon Riskini (Pump & Dump) hesaplar.
    """
    
    @staticmethod
    def detect_wyckoff_phase(df: pd.DataFrame, window: int = 50) -> str:
        """
        Fiyat ve Hacim ilişkisine bakarak Wyckoff döngüsünü tahmin eder.
        1. Accumulation (Toplama): Fiyat yatay/düşük, hacim artıyor.
        2. Markup (Yükseliş): Fiyat yükseliyor, hacim destekliyor.
        3. Distribution (Dağıtım): Fiyat yüksek/yatay, hacim çok yüksek (Mal çıkılıyor).
        4. Markdown (Çöküş): Fiyat düşüyor, hacim düşüyor veya panik satışı.
        """
        if df.empty or len(df) < window:
            return "UNKNOWN (Yetersiz Veri)"
            
        # Son X bar için metrikler
        recent_df = df.iloc[-window:]
        
        start_price = recent_df['close'].iloc[0]
        end_price = recent_df['close'].iloc[-1]
        price_change = (end_price - start_price) / start_price
        
        avg_volume_past = df['volume'].iloc[-(window*2):-window].mean() if len(df) >= window*2 else recent_df['volume'].mean()
        avg_volume_recent = recent_df['volume'].mean()
        
        # 0'a bölmeyi engelle
        vol_change = (avg_volume_recent / avg_volume_past) - 1 if avg_volume_past > 0 else 0
        
        # Yataylık kontrolü (Volatility / Range)
        max_p = recent_df['close'].max()
        min_p = recent_df['close'].min()
        price_range = (max_p - min_p) / min_p if min_p > 0 else 0
        
        # Basit Kural Tabanlı Wyckoff Sınıflandırması
        if price_range < 0.15 and vol_change > 0.2:
            return "ACCUMULATION (Akümülasyon / Kurumsal Toplama)"
        elif price_change > 0.15 and vol_change > 0:
            return "MARKUP (Yükseliş Trendi)"
        elif price_range < 0.20 and price_change > 0 and vol_change > 0.5:
            # Fiyat zirvede zorlanıyor ama hacim devasa artmış -> Mal dağıtımı
            return "DISTRIBUTION (Dağıtım / Kurumsal Çıkış)"
        elif price_change < -0.10:
            return "MARKDOWN (Düşüş Trendi / Çöküş)"
            
        return "CONSOLIDATION (Belirsiz Konsolidasyon)"

    @staticmethod
    def calculate_manipulation_risk(df: pd.DataFrame) -> Dict[str, Any]:
        """
        Pump & Dump veya Olağandışı Kurumsal Manipülasyon riskini ölçer.
        0-100 arası bir risk skoru döner.
        """
        risk_score = 0
        reasons = []
        
        if df.empty or len(df) < 20:
            return {"Risk_Score": 0, "Reasons": ["Yetersiz veri"]}
            
        # 1. Hacim Anormalliği (Volume Spike)
        vol_ma = df['volume'].rolling(20).mean()
        latest_vol = df['volume'].iloc[-1]
        prev_vol_ma = vol_ma.iloc[-2] if not pd.isna(vol_ma.iloc[-2]) else 1
        
        if latest_vol > (prev_vol_ma * 4): # Hacim 4 katına çıkmış
            risk_score += 40
            reasons.append("Olağandışı devasa hacim patlaması (Pump şüphesi).")
            
        # 2. İğne Boyları (Wick Size) - Fiyatın aşırı dalgalanıp geri dönmesi
        current = df.iloc[-1]
        body = abs(current['open'] - current['close'])
        total_range = current['high'] - current['low']
        
        if total_range > 0 and body / total_range < 0.2: 
            # Mumun %80'i iğne
            risk_score += 30
            reasons.append("Aşırı uzun iğne (Sert fiyat reddi / Stop avı).")
            
        # 3. Gap (Boşluklu) Açılışlar
        prev_close = df['close'].iloc[-2]
        gap_pct = abs(current['open'] - prev_close) / prev_close
        
        if gap_pct > 0.05: # %5'ten büyük gap
            risk_score += 20
            reasons.append("Sert boşluklu (GAP) açılış (Manipülatif fiyatlama).")
            
        risk_score = min(100, risk_score)
        
        risk_level = "DÜŞÜK"
        if risk_score > 70:
            risk_level = "YÜKSEK (Kritik Risk)"
        elif risk_score > 40:
            risk_level = "ORTA (Dikkatli Olun)"
            
        return {
            "Risk_Score": risk_score,
            "Risk_Level": risk_level,
            "Reasons": reasons if reasons else ["Olağandışı bir manipülasyon riski tespit edilmedi."]
        }
        
    @staticmethod
    def generate_ai_insight(df: pd.DataFrame) -> Dict[str, Any]:
        """Tüm Wyckoff ve Manipülasyon verisini harmanlayarak AI Kurumsal Özeti çıkarır."""
        wyckoff = SmartAI_Engine.detect_wyckoff_phase(df)
        manipulation = SmartAI_Engine.calculate_manipulation_risk(df)
        
        return {
            "Wyckoff_Phase": wyckoff,
            "Manipulation_Analysis": manipulation
        }
