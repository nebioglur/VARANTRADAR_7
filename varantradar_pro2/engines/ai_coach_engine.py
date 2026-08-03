from typing import Dict, Any, List
import pandas as pd
import numpy as np

class AICoachEngine:
    """
    Tüm analitik motorlardan gelen verileri (Korelasyon, Volatilite, Faktör) birleştirerek
    insan dilinde anlaşılabilir "Explainable AI" tarzı koçluk tavsiyeleri ve Sağlık Skorları üretir.
    """
    
    @staticmethod
    def evaluate_portfolio_health(
        diversification_score: float, 
        annual_volatility: float, 
        expected_return: float, 
        high_corr_count: int,
        liquidity_warnings: int = 0
    ) -> Dict[str, Any]:
        """
        Portföyün genel sağlık ve risk durumunu derecelendirir.
        """
        score = 100.0
        reasons = []
        
        # 1. Çeşitlendirme Etkisi (Diversification)
        if diversification_score < 1.1:
            score -= 20
            reasons.append("Çeşitlendirme Skoru (PDR) çok düşük. Aynı yöne giden varlıklar yoğunlukta.")
        elif diversification_score > 1.5:
            score += 10
            reasons.append("Portföy son derece iyi çeşitlendirilmiş (Mükemmel risk dağılımı).")
            
        # 2. Volatilite Etkisi (Risk)
        if annual_volatility > 40.0:
            score -= 15
            reasons.append(f"Portföy Volatilitesi çok yüksek (%{round(annual_volatility, 2)}). Sert dalgalanmalara hazırlıklı olun.")
        elif annual_volatility < 20.0:
            score += 5
            reasons.append(f"Portföy Volatilitesi düşük (%{round(annual_volatility, 2)}). Güvenli liman ağırlıklı.")
            
        # 3. Yüksek Korelasyon Riski
        if high_corr_count > 0:
            score -= (high_corr_count * 5)
            reasons.append(f"Portföyde birbiriyle yüksek korelasyonlu {high_corr_count} çift var. Çöküş anında koruma sağlamayabilirler.")
            
        # 4. Likidite Uyarıları
        if liquidity_warnings > 0:
            score -= (liquidity_warnings * 10)
            reasons.append("Bazı pozisyonlarınızda likidite riski var. Hızlı satışlarda büyük fiyat kaymaları (Slippage) yaşayabilirsiniz.")
            
        # 5. Getiri / Risk Beklentisi (Sharpe benzeri)
        if annual_volatility > 0:
            sharpe_proxy = expected_return / annual_volatility
            if sharpe_proxy > 1.0:
                score += 10
                reasons.append(f"Birim risk başına düşen beklenen getiri (Sharpe Ratio benzeri) çok yüksek.")
            elif sharpe_proxy < 0.5:
                score -= 10
                reasons.append(f"Birim risk başına düşen beklenen getiri düşük. Risk-Ödül dengesi bozuk olabilir.")
                
        # Skoru 0-100 arasına sınırla
        final_score = min(100.0, max(0.0, score))
        
        # Güven Endeksi (AI Confidence) - Verinin kalitesi ve sinyalin gücüne göre
        # Basitçe 70 + sağlık skoru bazlı
        confidence_score = 60 + (final_score * 0.35)
        
        return {
            "Portfolio_Health_Score": round(final_score, 1),
            "AI_Confidence_Score": round(confidence_score, 1),
            "Summary_Verdict": "Riskli" if final_score < 50 else ("Orta Riskli" if final_score < 75 else "Mükemmel Sağlık"),
            "Explainable_AI_Reasons": reasons
        }
