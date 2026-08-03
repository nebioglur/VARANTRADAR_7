import pandas as pd
from typing import Dict, Any, List

class ExplainableAIEngine:
    """
    Yapay zekanın aldığı kararları "insan diline" çevirerek açıklar (Explainable AI)
    ve alınan kararın risklerini/zıt argümanlarını (Counter Opinion) üretir.
    """
    
    @staticmethod
    def generate_explanation(decision: str, tech_indicators: Dict[str, Any], smart_money_score: int, vwap_distance: float) -> List[str]:
        """AI Kararının Arkasındaki Nedenleri Çıkarır"""
        reasons = []
        
        rsi = tech_indicators.get('RSI', 50)
        macd_hist = tech_indicators.get('MACD_Hist', 0)
        
        if "AL" in decision or "DEĞER" in decision:
            if smart_money_score >= 70:
                reasons.append("Kurumsal Para (Smart Money) hisseyi topluyor (Güçlü Akümülasyon).")
            if rsi < 40:
                reasons.append("Hisse aşırı satım bölgesine yakın (RSI < 40), potansiyel dip oluşumu var.")
            elif rsi > 60:
                reasons.append("Hissede güçlü bir trend (Momentum) mevcut.")
                
            if 0 <= vwap_distance <= 3:
                reasons.append("Fiyat, kurumsal ortalamaya (VWAP) çok yakın ve destek bulmuş durumda.")
            if macd_hist > 0:
                reasons.append("MACD histogramı pozitif bölgede, kısa vadeli yükseliş sinyali var.")
                
        elif "SAT" in decision or "DÜZELTME" in decision:
            if smart_money_score <= 30:
                reasons.append("Kurumsal para çıkışı (Dağıtım/Distribution) tespit edildi.")
            if rsi > 70:
                reasons.append("Hisse aşırı alım bölgesinde (RSI > 70), düzeltme ve satış baskısı gelebilir.")
            if vwap_distance < -2:
                reasons.append("Fiyat kurumsal ortalamanın (VWAP) altında kalmış, güçlü bir direnç baskısı var.")
            if macd_hist < 0:
                reasons.append("MACD histogramı negatif, momentum zayıflıyor.")
                
        if not reasons:
            reasons.append("Teknik ve hacim göstergeleri şu an için net bir ayrışma sunmuyor.")
            
        return reasons

    @staticmethod
    def generate_counter_opinion(decision: str, tech_indicators: Dict[str, Any], smart_money_score: int, vwap_distance: float, rv: float) -> List[str]:
        """Şeytanın Avukatlığı: Alınan kararın riskleri ve karşıt senaryosu."""
        risks = []
        
        rsi = tech_indicators.get('RSI', 50)
        
        if "AL" in decision or "DEĞER" in decision:
            if vwap_distance > 8:
                risks.append("Fiyat kurumsal ortalamadan (VWAP) çok fazla uzaklaştı. Hızlı bir kâr satışı/düzeltme gelebilir.")
            if rsi > 65:
                risks.append("Alım yönlü sinyal var ancak RSI çok yüksek. Trene geç kalmış olabilirsiniz.")
            if rv < 0.7:
                risks.append("Yükseliş sinyali var ama HACİM çok düşük. Sahte bir kırılım (Bull Trap) riski taşıyor.")
            if smart_money_score < 50:
                risks.append("Teknik sinyaller AL verse de, Akıllı Para (Smart Money) henüz güçlü bir giriş yapmadı.")
                
        elif "SAT" in decision or "DÜZELTME" in decision:
            if rsi < 30:
                risks.append("Satış baskısı güçlü ancak hisse çok ucuzladı. Aniden 'Tepki Alımları' gelebilir.")
            if smart_money_score > 60:
                risks.append("Fiyat düşüyor olsa da Kurumsal Para dipten gizlice mal topluyor olabilir.")
            if rv > 2.0:
                risks.append("Panik satışı çok hacimli. Çöküş hızlanabilir veya likidite avı (Stop patlatma) yapılıp fiyat aniden yukarı sürülebilir.")
                
        if not risks:
            risks.append("Mevcut verilerle yapay zeka belirgin bir zıt argüman (risk) bulamadı.")
            
        return risks
