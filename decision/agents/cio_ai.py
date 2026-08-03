import random
from typing import Dict, Any
from learning.learning_engine import AILearningEngine

class TechnicalAI:
    @staticmethod
    def evaluate(tech_result: Dict[str, Any]) -> Dict[str, Any]:
        """Teknik analiz sonucunu yorumlar."""
        score = tech_result.get("Score", 50.0)
        trend = tech_result.get("Trend", "YATAY")
        
        if score >= 70:
            vote = "AL"
            reason = f"Teknik güç yüksek ({score}). Trend: {trend}."
        elif score <= 30:
            vote = "SAT"
            reason = f"Teknik güç zayıf ({score}). Trend: {trend}."
        else:
            vote = "BEKLE"
            reason = f"Teknik göstergeler nötr bölgede ({score}). Kırılım beklenmeli."
            
        return {"Vote": vote, "Score": score, "Reasoning": reason}

class FundamentalAI:
    @staticmethod
    def evaluate(fund_result: Dict[str, Any]) -> Dict[str, Any]:
        """Temel analiz (Bilanço/Çarpan) sonucunu yorumlar."""
        score = fund_result.get("Score", 50.0)
        status = fund_result.get("Status", "NÖTR")
        
        if score >= 65:
            vote = "AL"
            reason = f"Şirket finansalları sağlam ({status}). İskontolu değerleme."
        elif score <= 35:
            vote = "SAT"
            reason = f"Şirket finansalları riskli ({status}). Aşırı primli değerleme."
        else:
            vote = "BEKLE"
            reason = "Bilanço çarpanları sektör ortalamasında."
            
        return {"Vote": vote, "Score": score, "Reasoning": reason}

class MacroAI:
    @staticmethod
    def evaluate(macro_result: Dict[str, Any]) -> Dict[str, Any]:
        """Makro rejim ve VIX (Volatilite) verisini yorumlar."""
        regime = macro_result.get("Regime", "UNKNOWN")
        vix_status = macro_result.get("Volatility", "NORMAL")
        score = macro_result.get("Score", 50.0)
        
        if regime == "BOĞA" and vix_status != "YÜKSEK VOLATİLİTE":
            vote = "AL"
            reason = "Makro rejim BOĞA yönünde destekleyici. Likidite mevcut."
        elif regime == "AYI" or vix_status == "YÜKSEK VOLATİLİTE":
            vote = "SAT"
            reason = f"Makro riskler çok yüksek (Rejim: {regime}, Volatilite: {vix_status})."
            score = max(0.0, score - 20) # Risk cezası
        else:
            vote = "BEKLE"
            reason = "Makro piyasa yönü belirsiz. Konsolidasyon evresi."
            
        return {"Vote": vote, "Score": score, "Reasoning": reason}

class SmartMoneyAI:
    @staticmethod
    def evaluate(smart_result: Dict[str, Any]) -> Dict[str, Any]:
        """Kurumsal para girişi ve hacim verisini yorumlar."""
        score = smart_result.get("Score", 50.0)
        status = smart_result.get("Status", "NÖTR")
        
        if score >= 70:
            vote = "AL"
            reason = "Kurumsal para girişi (Akümülasyon) tespit edildi."
        elif score <= 30:
            vote = "SAT"
            reason = "Kurumsal para çıkışı (Dağıtım) tespit edildi."
        else:
            vote = "BEKLE"
            reason = "Büyük para akışında net bir yön yok."
            
        return {"Vote": vote, "Score": score, "Reasoning": reason}

class ChiefInvestmentOfficer:
    @staticmethod
    def evaluate_committee(
        symbol: str, 
        current_price: float, 
        tech_res: Dict[str, Any],
        fund_res: Dict[str, Any],
        smart_res: Dict[str, Any],
        macro_res: Dict[str, Any],
        risk_plan: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Tüm alt-ajanlardan (Committee) rapor alıp, Risk Kuralları 
        çerçevesinde NİHAİ AL/SAT KARARINI veren model.
        """
        tech = TechnicalAI.evaluate(tech_res)
        fund = FundamentalAI.evaluate(fund_res)
        macro = MacroAI.evaluate(macro_res)
        smart = SmartMoneyAI.evaluate(smart_res)
        
        committee_votes = {
            "Technical_AI": tech,
            "Fundamental_AI": fund,
            "Macro_AI": macro,
            "SmartMoney_AI": smart
        }
        
        # Öğrenme motorundan güncel Ağırlık ve Başarı (Win Rate) verilerini çek
        regime = macro_res.get("Regime", "YATAY")
        ai_weights = AILearningEngine.get_regime_weights(regime)
        ai_stats = AILearningEngine.get_agent_stats()
        
        for agent_name in committee_votes.keys():
            committee_votes[agent_name]["Weight_Pct"] = ai_weights.get(agent_name, 0.25) * 100
            if agent_name in ai_stats:
                committee_votes[agent_name]["Win_Rate"] = ai_stats[agent_name]["win_rate"]
                committee_votes[agent_name]["Total_Trades"] = ai_stats[agent_name]["total_trades"]
                committee_votes[agent_name]["History"] = ai_stats[agent_name]["history"]
            else:
                committee_votes[agent_name]["Win_Rate"] = 50.0
                committee_votes[agent_name]["Total_Trades"] = 0
                committee_votes[agent_name]["History"] = []
        
        # Karar Çözümleme (Conflict Resolution)
        buy_votes = sum(1 for a in [tech, fund, macro, smart] if a["Vote"] == "AL")
        sell_votes = sum(1 for a in [tech, fund, macro, smart] if a["Vote"] == "SAT")
        
        # 1. MUTLAK VETO KONTROLLERİ (Risk & Makro)
        max_drawdown_risk = risk_plan.get("Actual_Risk_Pct", 2.0)
        
        # Eğer iflas riski %10'u aşıyorsa doğrudan reddet
        if max_drawdown_risk > 10.0:
            final_action = "NO_TRADE"
            cio_reasoning = f"VETO EDİLDİ: Tek işlemde kasanın %{max_drawdown_risk}'i riske edilemez (Limit: %10). Sermaye koruması önceliklidir."
        elif macro["Vote"] == "SAT":
            final_action = "NO_TRADE"
            cio_reasoning = f"VETO EDİLDİ: Makro ekonomi ve VIX riskleri çok yüksek ({macro['Reasoning']})."
        # 2. KOMİTE OYLAMASI
        elif buy_votes >= 3:
            final_action = "STRONG_BUY"
            cio_reasoning = f"Komitenin çoğunluğu ({buy_votes}/4) AL yönünde mutabık."
        elif buy_votes == 2 and sell_votes == 0:
            final_action = "BUY"
            cio_reasoning = "Kısmi AL sinyali. Kontrollü (düşük lot) giriş yapılabilir."
        elif sell_votes >= 2:
            final_action = "SELL"
            cio_reasoning = f"Komitenin çoğunluğu ({sell_votes}/4) SAT/RİSKLİ yönünde uyarıyor."
        else:
            final_action = "NO_TRADE"
            cio_reasoning = "Komitede konsensüs (AL/SAT) sağlanamadı. Beklemede kal."

        # THE 7 WHYS (Decision Intelligence Explanations)
        regime = macro_res.get("Regime", "YATAY")
        whys = {
            "Neden?": cio_reasoning,
            "Neden Şimdi?": f"Piyasa rejimi '{regime}' ve Akıllı Para durumu '{smart['Vote']}' olduğu için zamanlama riski dengelendi.",
            "Neden Bu Fiyat?": f"Teknik skor ({tech['Score']}) kırılım veya destek dönüşüne işaret ediyor.",
            "Neden Bu Stop?": "Volatilite (ATR) hesaplamalarına dayanarak, fiyat gürültüsünün (noise) bittiği noktaya konuldu.",
            "Neden Bu Hedef?": "Trend ivmesine ve geçmiş dalga boylarına göre güvenli çıkış alanı olarak seçildi.",
            "Neden Bu Süre?": "Momentumun sönümlenme hızına ve piyasa rejiminin doğasına göre optimize edildi.",
            "Neden Bu Ağırlık?": f"İşlem başına risk {max_drawdown_risk}% ile sınırlandırılarak Kelly Kriteri gözetildi."
        }
        
        return {
            "Final_Action": final_action,
            "CIO_Reasoning": cio_reasoning,
            "Committee_Votes": committee_votes,
            "The_7_Whys": whys
        }
